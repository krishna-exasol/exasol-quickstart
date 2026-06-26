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
def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, total: int, msg: str) -> None:
    say(f"\n[{n}/{total}] {msg}")


def ok(msg: str) -> None:
    say(f"    + {msg}")


def warn(msg: str) -> None:
    say(f"    ! {msg}")


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    say(f"\nError: {msg}")
    raise SystemExit(1)


def run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


# ------------------------------------------------------------------- platform
def detect() -> tuple[str, str]:
    return platform.system().lower(), platform.machine().lower()


def recommended_base(system: str, arch: str) -> str:
    """The base recommended by the docs for this OS."""
    if system == "darwin" and arch in ("arm64", "aarch64"):
        return "personal"          # native VM, no Docker
    if system == "linux":
        return "nano-native"       # native .run, no Docker
    return "nano-docker"           # Windows (and the universally-tested path)


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

    say("\nPlan: Exasol Nano (database) + Exasol MCP server (sidecar)"
        + (" + JSON Tables (sidecar)" if with_json_tables else ""))
    say("  network: " + NETWORK)
    say("  db : " + " ".join(db_cmd))
    say("  mcp: " + " ".join(mcp_cmd))
    if with_json_tables:
        say(f"  jt : {JT_CONTAINER} from {JT_IMAGE} (built once from source: Python + Rust)")
    if dry_run:
        say("\n(dry run - nothing executed)")
        return 0

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
    say("\n" + "=" * 62)
    say("  Exasol quickstart is up")
    say("=" * 62)
    say(f"  Database : 127.0.0.1:{SQL_PORT}   (user sys / password exasol)")
    say(f"  Web UI   : https://127.0.0.1:{UI_PORT}")
    say(f"  MCP      : http://127.0.0.1:{mcp_port}/mcp   (point your LLM client here)")
    if jt_running:
        say(f"  JSON     : exasol-quickstart json-tables --help")
        say(f"             (put files in the '{JT_WORKSPACE_VOL}' volume, then ingest-and-wrap)")
    stop = f"docker rm -f {DB_CONTAINER} {MCP_CONTAINER}" + (f" {JT_CONTAINER}" if jt_running else "")
    say(f"  Stop     : {stop}")
    say("")


# --------------------------------------------------------- experimental paths
def not_yet(base: str, system: str, arch: str) -> int:
    say(f"\nThe recommended base for {system}/{arch} is '{base}', which is not yet "
        "automated in this release.")
    say("\nWhat works today (any OS with Docker):")
    say("    exasol-quickstart --base nano-docker")
    say(f"\nThe full '{base}' flow is on the roadmap — see:\n    {DOCS_URL}")
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
    say(f"exasol-quickstart {__version__}  -  platform: {system}/{arch}")

    # The one base that works on every OS today. (Native no-Docker bases per OS
    # arrive in 0.3.0; until then the bare command always uses Nano + Docker.)
    base = args.base if args.base != "auto" else "nano-docker"
    say(f"Base: {base}" + ("  (default)" if args.base == "auto" else "  (forced)"))

    if base == "nano-docker":
        return nano_docker(not args.no_json_tables, args.mcp_port, args.dry_run)
    return not_yet(base, system, arch)


if __name__ == "__main__":
    sys.exit(main())
