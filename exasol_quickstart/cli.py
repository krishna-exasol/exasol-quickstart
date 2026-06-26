"""exasol-quickstart — one command to try Exasol with AI add-ons.

Detects the platform, brings up an Exasol base database, and layers the
MCP server (and, later, JSON Tables) on top. See the design + decision graph:
https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/

0.1.x ships the reliable, public-image path: Exasol Nano (database) + the
official Exasol MCP server image as a sidecar on a shared Docker network. (The
Nano "stack" system is not in the public image yet, so we use two containers.)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

from . import __version__

DOCS_URL = "https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/"

NANO_IMAGE = "exasol/nano:latest"
MCP_IMAGE = "exasol/mcp-server:latest"
NETWORK = "exasol-quickstart-net"
DB_CONTAINER = "exasol-quickstart-db"
MCP_CONTAINER = "exasol-quickstart-mcp"
VOLUME = "exasol-quickstart-data"
SQL_PORT = 8563
UI_PORT = 8443
MCP_PORT = 4896

JT_CONTAINER = "exasol-quickstart-json-tables"
JT_IMAGE = "exasol-quickstart-json-tables:latest"
JT_WORKSPACE_VOL = "exasol-quickstart-workspace"
JT_REPO = "https://github.com/exasol-labs/exasol-json-tables.git"
JT_REF = "main"

# JSON Tables is Python + a Rust ingest engine with no published image, so we build
# one locally (once) from this Dockerfile. The CLI is exec'd into the standing container.
DOCKERFILE_JSON_TABLES = """\
FROM python:3.12-slim
ARG EXASOL_JSON_TABLES_REPOSITORY
ARG EXASOL_JSON_TABLES_REF
RUN apt-get update \\
    && apt-get install -y --no-install-recommends build-essential ca-certificates curl git \\
    && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs \\
        | sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"
RUN git clone "${EXASOL_JSON_TABLES_REPOSITORY}" /opt/exasol-json-tables \\
    && cd /opt/exasol-json-tables && git checkout "${EXASOL_JSON_TABLES_REF}"
WORKDIR /opt/exasol-json-tables
RUN python -m pip install --no-cache-dir --upgrade pip \\
    && python -m pip install --no-cache-dir -e . \\
    && cargo build --manifest-path crates/json_tables_ingest/Cargo.toml
"""


# --------------------------------------------------------------------------- UI
try:  # make Unicode + ANSI work on the Windows console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass
if sys.platform == "win32":
    try:
        import ctypes
        _k = ctypes.windll.kernel32  # type: ignore[attr-defined]
        _k.SetConsoleMode(_k.GetStdHandle(-11), 7)
    except Exception:
        pass

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
def _c(code: str) -> str:
    return code if _COLOR else ""
RESET, BOLD, DIM = _c("\033[0m"), _c("\033[1m"), _c("\033[2m")
CYAN, GREEN, YELLOW = _c("\033[36m"), _c("\033[32m"), _c("\033[33m")
BLUE, RED = _c("\033[34m"), _c("\033[31m")
_RULE = "─" * 54


def say(msg: str = "") -> None:
    print(msg, flush=True)


def banner() -> None:
    say()
    say(f"  {YELLOW}⚡{RESET} {BOLD}exasol-quickstart{RESET} {DIM}v{__version__}{RESET}")


def rule() -> None:
    say(f"  {DIM}{_RULE}{RESET}")


def kv(key: str, val: str, note: str = "") -> None:
    tail = f"  {DIM}{note}{RESET}" if note else ""
    say(f"  {DIM}{key.ljust(9)}{RESET} {val}{tail}")


def heading(text: str) -> None:
    say()
    say(f"  {BOLD}{text}{RESET}")
    rule()


def step(n: int, total: int, msg: str) -> None:
    say(f"\n  {CYAN}[{n}/{total}]{RESET} {BOLD}{msg}{RESET}")


def ok(msg: str) -> None:
    say(f"      {GREEN}✓{RESET} {DIM}{msg}{RESET}")


def warn(msg: str) -> None:
    say(f"      {YELLOW}!{RESET} {msg}")


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    say(f"\n  {RED}✗ Error{RESET}  {msg}\n")
    raise SystemExit(1)


def run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def render_plan(title: str, steps: list[tuple[str, str]],
                endpoints: list[tuple[str, str, str]]) -> None:
    """Pretty, readable plan: numbered steps + an endpoints panel."""
    heading(f"Plan  {DIM}·{RESET}  {title}")
    say()
    w = max((len(s[0]) for s in steps), default=0) + 3
    for i, (what, detail) in enumerate(steps, 1):
        say(f"   {CYAN}{i}{RESET}  {what.ljust(w)}{DIM}{detail}{RESET}")
    say()
    say(f"  {BOLD}When it's up{RESET}")
    for label, addr, note in endpoints:
        tail = f"   {DIM}{note}{RESET}" if note else ""
        say(f"      {GREEN}●{RESET} {DIM}{label.ljust(9)}{RESET}{addr}{tail}")


# ------------------------------------------------------------------- platform
def detect() -> tuple[str, str]:
    return platform.system().lower(), platform.machine().lower()


def recommended_base(system: str, arch: str) -> str:
    """The base recommended by the docs for this OS (ignores Docker availability)."""
    if system == "darwin" and arch in ("arm64", "aarch64"):
        return "personal"          # native VM, no Docker
    if system == "linux":
        return "nano-native"       # native .run, no Docker
    return "nano-docker"


def choose_base(system: str, arch: str) -> str:
    """Auto base selection.

    Prefer the tested Nano + Docker bundle whenever Docker is available. When it is
    not, fall back to the only *implemented* no-Docker base — Exasol Personal on
    macOS. Everywhere else (Linux / Windows) Docker is the working path today, so we
    select nano-docker and surface a clear "start Docker" message if it's missing.
    (Native Nano `.run` on Linux is on the roadmap; reach it via --base nano-native.)
    """
    if docker_ready():
        return "nano-docker"
    if system == "darwin" and arch in ("arm64", "aarch64"):
        return "personal"
    return "nano-docker"


# ------------------------------------------------------------------- helpers
def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def docker_ready() -> bool:
    return have("docker") and run(["docker", "info"], check=False, capture=True).returncode == 0


def wait_tcp(host: str, port: int, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            time.sleep(3)
    return False


def wait_http(url: str, timeout: int = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(3)
    return False


# ----------------------------------------------------------------- json-tables
def image_exists(image: str) -> bool:
    r = run(["docker", "images", "-q", image], check=False, capture=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def build_jt_image() -> bool:
    """Build the JSON Tables sidecar image (once). Returns True on success."""
    import tempfile
    ctx = tempfile.mkdtemp(prefix="exq-jt-")
    with open(f"{ctx}/Dockerfile", "w", encoding="utf-8") as fh:
        fh.write(DOCKERFILE_JSON_TABLES)
    cmd = ["docker", "build", "-t", JT_IMAGE,
           "--build-arg", f"EXASOL_JSON_TABLES_REPOSITORY={JT_REPO}",
           "--build-arg", f"EXASOL_JSON_TABLES_REF={JT_REF}", ctx]
    return run(cmd, check=False).returncode == 0


def run_jt_sidecar() -> None:
    run(["docker", "rm", "-f", JT_CONTAINER], check=False, capture=True)
    # Standing container: keep it alive, exec the CLI on demand.
    run(["docker", "run", "-d", "--name", JT_CONTAINER, "--network", NETWORK,
         "-v", f"{JT_WORKSPACE_VOL}:/workspace", "-w", "/workspace",
         "--entrypoint", "sleep", JT_IMAGE, "infinity"])


def jt_passthrough(extra: list[str]) -> int:
    """`exasol-quickstart json-tables <args>` -> run the CLI inside the sidecar."""
    if not docker_ready():
        die("Docker is not running.")
    if not run(["docker", "ps", "-q", "-f", f"name=^{JT_CONTAINER}$"], capture=True).stdout.strip():
        die(f"JSON Tables container isn't running. Start the bundle first: exasol-quickstart")
    cmd = ["docker", "exec", JT_CONTAINER, "exasol-json-tables", *extra,
           "--dsn", f"{DB_CONTAINER}:{SQL_PORT}", "--user", "sys", "--password", "exasol"]
    return run(cmd, check=False).returncode


# ----------------------------------------------------------------- nano/docker
def nano_docker(with_json_tables: bool, mcp_port: int, dry_run: bool) -> int:
    db_cmd = [
        "docker", "run", "-d", "--name", DB_CONTAINER, "--network", NETWORK,
        "--shm-size=1g",
        "-p", f"127.0.0.1:{SQL_PORT}:{SQL_PORT}",
        "-p", f"127.0.0.1:{UI_PORT}:{UI_PORT}",
        "-v", f"{VOLUME}:/exa",
        NANO_IMAGE,
    ]
    mcp_cmd = [
        "docker", "run", "-d", "--name", MCP_CONTAINER, "--network", NETWORK,
        "-p", f"127.0.0.1:{mcp_port}:{MCP_PORT}",
        "-e", f"EXA_DSN={DB_CONTAINER}:{SQL_PORT}",
        "-e", "EXA_USER=sys",
        "-e", "EXA_PASSWORD=exasol",
        "-e", "EXA_SSL_CERT_VALIDATION=false",
        "-e", 'EXA_MCP_SETTINGS={"enable_read_query": true}',
        MCP_IMAGE,
        "--host", "0.0.0.0", "--port", str(MCP_PORT), "--no-auth",
    ]

    title = "Exasol Nano + MCP" + (" + JSON Tables" if with_json_tables else "") + f"  {DIM}(Docker){RESET}"
    plan_steps = [
        ("Create a private Docker network", NETWORK),
        ("Start Exasol Nano (database)", f"{NANO_IMAGE}"),
        ("Start the MCP server (sidecar)", f"{MCP_IMAGE}"),
    ]
    if with_json_tables:
        plan_steps.append(("Build & start JSON Tables", "first run compiles a Rust engine"))
    endpoints = [
        ("Database", f"127.0.0.1:{SQL_PORT}", "user sys / password exasol"),
        ("Web UI", f"https://127.0.0.1:{UI_PORT}", ""),
        ("MCP", f"http://127.0.0.1:{mcp_port}/mcp", "point your LLM client here"),
    ]
    if with_json_tables:
        endpoints.append(("JSON", "exasol-quickstart json-tables …", "ingest JSON → SQL"))

    render_plan(title, plan_steps, endpoints)

    if dry_run:
        say()
        say(f"  {DIM}Exact commands:{RESET}")
        for c in ([db_cmd, mcp_cmd]):
            say(f"  {DIM}$ {' '.join(c)}{RESET}")
        if with_json_tables:
            say(f"  {DIM}$ docker build -t {JT_IMAGE} …  (then run as a sidecar){RESET}")
        say()
        say(f"  {YELLOW}Dry run{RESET} {DIM}— nothing was executed.{RESET}\n")
        return 0
    say()

    total = 6 if with_json_tables else 5
    step(1, total, "Checking Docker")
    if not docker_ready():
        die("Docker is not installed or not running. Start Docker and retry "
            "(or use --dry-run to see the plan).")
    ok("Docker engine is running")

    step(2, total, "Preparing network and clearing any previous run")
    run(["docker", "rm", "-f", DB_CONTAINER, MCP_CONTAINER, JT_CONTAINER], check=False, capture=True)
    run(["docker", "network", "create", NETWORK], check=False, capture=True)
    ok("ready")

    step(3, total, f"Starting Exasol Nano ({NANO_IMAGE})")
    run(db_cmd)
    if wait_tcp("127.0.0.1", SQL_PORT, timeout=180):
        ok(f"database accepting connections on 127.0.0.1:{SQL_PORT}")
    else:
        warn("database port not open yet; it may still be initialising "
             f"(docker logs -f {DB_CONTAINER}).")

    step(4, total, f"Starting the Exasol MCP server ({MCP_IMAGE})")
    run(mcp_cmd)
    ok(f"container '{MCP_CONTAINER}' started")

    step(5, total, "Waiting for the MCP endpoint")
    if wait_http(f"http://127.0.0.1:{mcp_port}/health"):
        ok(f"MCP is healthy at http://127.0.0.1:{mcp_port}/mcp")
    else:
        warn(f"MCP not healthy yet; check: docker logs -f {MCP_CONTAINER}")

    jt_running = False
    if with_json_tables:
        step(6, total, "Starting JSON Tables")
        if not image_exists(JT_IMAGE):
            say("    building the JSON Tables image (one-time; compiles a Rust engine, a few minutes)...")
            if not build_jt_image():
                warn("JSON Tables image build failed; skipping it. Re-run later to retry. "
                     "(Nano + MCP are up.)")
            else:
                ok("image built")
        if image_exists(JT_IMAGE):
            run_jt_sidecar()
            jt_running = True
            ok(f"container '{JT_CONTAINER}' running")

    summary(mcp_port, jt_running)
    return 0


def summary(mcp_port: int, jt_running: bool = False) -> None:
    heading(f"{GREEN}✓ Exasol quickstart is up{RESET}")
    say()
    kv("Database", f"127.0.0.1:{SQL_PORT}", "user sys / password exasol")
    kv("Web UI", f"https://127.0.0.1:{UI_PORT}")
    kv("MCP", f"http://127.0.0.1:{mcp_port}/mcp", "point your LLM client here")
    if jt_running:
        kv("JSON", "exasol-quickstart json-tables --help", "ingest JSON → SQL")
    say()
    stop = f"docker rm -f {DB_CONTAINER} {MCP_CONTAINER}" + (f" {JT_CONTAINER}" if jt_running else "")
    kv("Stop", f"{DIM}{stop}{RESET}")
    say()


# --------------------------------------------------------- native (no-Docker) bases
PERSONAL_INSTALLER = "https://downloads.exasol.com/exasol-personal/installer.sh"


def resolve_launcher() -> str | None:
    if have("exasol"):
        return "exasol"
    cand = os.path.expanduser("~/.local/bin/exasol")
    return cand if os.path.exists(cand) else None


def personal(with_json_tables: bool, mcp_port: int, dry_run: bool) -> int:
    """macOS (Apple Silicon) host path: Exasol Personal local + MCP on the host.

    EXPERIMENTAL — implemented from the documented launcher behaviour but not yet
    validated end-to-end. If anything fails, fall back to `--base nano-docker`.
    """
    title = "Exasol Personal + MCP" + (" + JSON Tables" if with_json_tables else "") + f"  {DIM}(no Docker · macOS){RESET}"
    plan_steps = [
        ("Install / verify the exasol launcher", "~/.local/bin/exasol"),
        ("Provision a local Personal database", "exasol install local  (~10–20 min)"),
        ("Discover the connection", "exasol info --json"),
        ("Install & start the MCP server", f"pipx · port {mcp_port}"),
    ]
    if with_json_tables:
        plan_steps.append(("Set up JSON Tables on the host", "venv + Rust (guided)"))
    endpoints = [
        ("Database", "127.0.0.1:<dbPort>", "discovered at install time"),
        ("MCP", f"http://127.0.0.1:{mcp_port}/mcp", "point your LLM client here"),
    ]
    render_plan(title, plan_steps, endpoints)
    say()
    warn("Experimental macOS path — not yet validated end-to-end. "
         "If anything fails, use --base nano-docker (needs Docker).")

    if dry_run:
        say()
        say(f"  {YELLOW}Dry run{RESET} {DIM}— nothing was executed.{RESET}\n")
        return 0
    say()

    exe = resolve_launcher()
    if not exe:
        say("\nInstalling the Exasol Personal launcher...")
        if not have("curl"):
            die("curl is required to install the launcher.")
        run(["sh", "-c", f"curl -fsSL {PERSONAL_INSTALLER} | sh"], check=False)
        exe = resolve_launcher() or die(
            "launcher still not found; add ~/.local/bin to PATH and retry.")
    ok(f"launcher: {exe}")

    if run([exe, "info", "--json"], check=False, capture=True).returncode != 0:
        warn("no deployment found; running `exasol install local` (this can take 10-20 min)...")
        if run([exe, "install", "local"], check=False).returncode != 0:
            die("`exasol install local` failed (macOS Apple-Silicon only). See the launcher output.")
    else:
        run([exe, "start"], check=False, capture=True)

    info_raw = run([exe, "info", "--json"], check=False, capture=True).stdout
    try:
        info = json.loads(info_raw)
        conn = info.get("connection", {})
        port = conn.get("dbPort") or SQL_PORT
        user = conn.get("username") or "sys"
        deploy_dir = info.get("deploymentDir") or ""
    except Exception:
        die("could not read `exasol info --json`. Try `exasol info`.")
    password = "exasol"
    secrets = os.path.join(deploy_dir, "secrets.json") if deploy_dir else ""
    if secrets and os.path.exists(secrets):
        try:
            password = json.load(open(secrets, encoding="utf-8")).get("dbPassword", "exasol")
        except Exception:
            pass
    ok(f"database: 127.0.0.1:{port}  (user {user})")

    say("\nInstalling and starting the MCP server (pipx)...")
    run(["pipx", "install", "exasol-mcp-server"], check=False)
    env = dict(os.environ, EXA_DSN=f"127.0.0.1:{port}", EXA_USER=user,
               EXA_PASSWORD=str(password), EXA_SSL_CERT_VALIDATION="false")
    try:
        subprocess.Popen(
            ["exasol-mcp-server-http", "--host", "127.0.0.1", "--port", str(mcp_port), "--no-auth"],
            env=env)
        ok(f"MCP starting at http://127.0.0.1:{mcp_port}/mcp")
    except FileNotFoundError:
        warn("could not launch exasol-mcp-server-http; ensure pipx's bin dir is on PATH, "
             f"then run it manually with EXA_DSN=127.0.0.1:{port}.")

    if with_json_tables:
        say("\nJSON Tables (host) — one-time setup (needs Python 3.10+ and a Rust toolchain):")
        say("    git clone https://github.com/exasol-labs/exasol-json-tables.git")
        say("    cd exasol-json-tables && python3 -m pip install -e .")
        say(f"    exasol-json-tables ingest-and-wrap --input data.json --name demo \\")
        say(f"        --dsn 127.0.0.1:{port} --user {user} --password <password>")

    heading(f"{GREEN}✓ Exasol Personal quickstart{RESET} {DIM}(experimental){RESET}")
    say()
    kv("Database", f"127.0.0.1:{port}", f"user {user}")
    kv("MCP", f"http://127.0.0.1:{mcp_port}/mcp", "point your LLM client here")
    say()
    return 0


def nano_native(system: str, arch: str) -> int:
    heading("Linux native (Nano .run, no Docker)")
    say()
    warn("Not auto-installed yet. On Linux the reliable path today is the Docker bundle:")
    say(f"        {CYAN}exasol-quickstart --base nano-docker{RESET}")
    say(f"\n  {DIM}Native .run automation is on the roadmap.{RESET}\n")
    return 2


# ----------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="exasol-quickstart",
        description="One command to try Exasol with AI add-ons (MCP server, JSON Tables).",
    )
    p.add_argument("--base", choices=["auto", "nano-docker", "nano-native", "personal"],
                   default="auto", help="Force a specific base (default: auto by OS).")
    p.add_argument("--no-json-tables", action="store_true",
                   help="Skip the JSON Tables add-on (it's included by default).")
    p.add_argument("--mcp-port", type=int, default=MCP_PORT,
                   help=f"Host port for the MCP endpoint (default {MCP_PORT}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show the plan without executing anything.")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Run non-interactively (assume yes).")
    p.add_argument("--version", action="version", version=f"exasol-quickstart {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # `exasol-quickstart json-tables <args>` -> run the JSON Tables CLI in its sidecar.
    if argv and argv[0] == "json-tables":
        return jt_passthrough(argv[1:])

    args = build_parser().parse_args(argv)
    system, arch = detect()
    banner()
    kv("Platform", f"{system} / {arch}")

    # Auto: prefer the tested Nano+Docker bundle when Docker is available; otherwise
    # fall back to the OS-native no-Docker base.
    base = args.base if args.base != "auto" else choose_base(system, arch)
    kv("Base", base, "auto-selected" if args.base == "auto" else "forced")

    with_jt = not args.no_json_tables
    if base == "nano-docker":
        return nano_docker(with_jt, args.mcp_port, args.dry_run)
    if base == "personal":
        return personal(with_jt, args.mcp_port, args.dry_run)
    return nano_native(system, arch)


if __name__ == "__main__":
    sys.exit(main())
