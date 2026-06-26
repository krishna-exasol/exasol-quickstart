"""exasol-quickstart — one command to try Exasol with AI add-ons.

Detects the platform, brings up an Exasol base database, and layers the
MCP server (and optionally JSON Tables) on top. See the design + decision graph:
https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

from . import __version__

DOCS_URL = "https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/"

NANO_IMAGE = "exasol/nano:latest"
CONTAINER = "exasol-quickstart"
VOLUME = "exasol-quickstart-data"
SQL_PORT = 8563
UI_PORT = 8443
MCP_PORT = 4896


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
    return subprocess.run(cmd, check=check, text=True,
                          capture_output=capture)


# ------------------------------------------------------------------- platform
def detect() -> tuple[str, str]:
    system = platform.system().lower()      # 'darwin' | 'linux' | 'windows'
    arch = platform.machine().lower()       # 'arm64'/'aarch64' | 'x86_64'/'amd64'
    return system, arch


def recommended_base(system: str, arch: str) -> str:
    """The base recommended by the docs for this OS."""
    if system == "darwin" and arch in ("arm64", "aarch64"):
        return "personal"          # native VM, no Docker
    if system == "linux":
        return "nano-native"       # native .run, no Docker
    return "nano-docker"           # Windows (and the universally-tested path)


# ----------------------------------------------------------------- nano/docker
def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def docker_ready() -> bool:
    if not have("docker"):
        return False
    return run(["docker", "info"], check=False, capture=True).returncode == 0


def mcp_healthy(port: int, timeout: int = 180) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def nano_docker(addons: list[str], mcp_port: int, dry_run: bool, assume_yes: bool) -> int:
    stacks = ["mcp-server"]
    cmd = [
        "docker", "run", "-d", "--name", CONTAINER,
        "--shm-size=1g",
        "-p", f"127.0.0.1:{SQL_PORT}:{SQL_PORT}",
        "-p", f"127.0.0.1:{UI_PORT}:{UI_PORT}",
        "-p", f"127.0.0.1:{mcp_port}:{MCP_PORT}",
        "-v", f"{VOLUME}:/exa",
        NANO_IMAGE,
        "--provision-stacks", ",".join(stacks),
    ]

    say("\nPlan: Exasol Nano (Docker) + MCP server")
    say("  " + " ".join(cmd))
    if "json-tables" in addons:
        warn("JSON Tables for the Nano base is experimental and not wired in 0.1.0 "
             "(needs a custom Nano stack). Skipping it for now — see the docs.")
    if dry_run:
        say("\n(dry run - nothing executed)")
        return 0

    total = 4
    step(1, total, "Checking Docker")
    if not docker_ready():
        die("Docker is not installed or not running. Start Docker Desktop and retry, "
            "or run with --dry-run to see the plan.")
    ok("Docker engine is running")

    step(2, total, "Removing any previous quickstart container")
    run(["docker", "rm", "-f", CONTAINER], check=False, capture=True)
    ok("clean")

    step(3, total, f"Starting Exasol Nano + MCP (first run pulls {NANO_IMAGE} and provisions stacks)")
    say("    this can take a few minutes on the first run...")
    run(cmd)
    ok(f"container '{CONTAINER}' started")

    step(4, total, "Waiting for the MCP endpoint to come up")
    if mcp_healthy(mcp_port):
        ok(f"MCP is healthy at http://127.0.0.1:{mcp_port}/mcp")
    else:
        warn("MCP did not report healthy yet; it may still be provisioning. "
             f"Check: docker logs -f {CONTAINER}")

    summary(mcp_port)
    return 0


def summary(mcp_port: int) -> None:
    say("\n" + "=" * 60)
    say("  Exasol quickstart is up")
    say("=" * 60)
    say(f"  Database : 127.0.0.1:{SQL_PORT}   (user sys / password exasol)")
    say(f"  Web UI   : https://127.0.0.1:{UI_PORT}")
    say(f"  MCP      : http://127.0.0.1:{mcp_port}/mcp   (point your LLM client here)")
    say(f"  Logs     : docker logs -f {CONTAINER}")
    say(f"  Stop     : docker rm -f {CONTAINER}")
    say("")


# --------------------------------------------------------- experimental paths
def not_yet(base: str, system: str, arch: str, mcp_port: int) -> int:
    say(f"\nThe recommended base for {system}/{arch} is '{base}', which is not yet "
        "automated in this 0.1.0 release.")
    say("\nWhat 0.1.0 supports today:")
    say("  - The Nano-via-Docker base + MCP, on any OS with Docker:")
    say("        exasol-quickstart --base nano-docker")
    say(f"\nThe full '{base}' flow (and JSON Tables) is on the roadmap — see:")
    say(f"  {DOCS_URL}")
    return 2


# ----------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="exasol-quickstart",
        description="One command to try Exasol with AI add-ons (MCP server, JSON Tables).",
    )
    p.add_argument("--base", choices=["auto", "nano-docker", "nano-native", "personal"],
                   default="auto", help="Force a specific base (default: auto by OS).")
    p.add_argument("--with", dest="addons", action="append", default=[],
                   choices=["json-tables"], metavar="ADDON",
                   help="Add-ons to install (e.g. --with json-tables).")
    p.add_argument("--mcp-port", type=int, default=MCP_PORT,
                   help=f"Host port for the MCP endpoint (default {MCP_PORT}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show the plan without executing anything.")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Run non-interactively (assume yes).")
    p.add_argument("--version", action="version", version=f"exasol-quickstart {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    system, arch = detect()

    say(f"exasol-quickstart {__version__}  -  platform: {system}/{arch}")

    base = args.base if args.base != "auto" else recommended_base(system, arch)
    say(f"Base: {base}" + ("  (auto-selected)" if args.base == "auto" else "  (forced)"))

    if base == "nano-docker":
        return nano_docker(args.addons, args.mcp_port, args.dry_run, args.yes)

    # nano-native / personal: real flows are on the roadmap; guide the user for now.
    if args.dry_run:
        return not_yet(base, system, arch, args.mcp_port)
    return not_yet(base, system, arch, args.mcp_port)


if __name__ == "__main__":
    sys.exit(main())
