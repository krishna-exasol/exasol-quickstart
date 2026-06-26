"""Console entry point for `exasol-quickstart`.

This is the 0.0.1 placeholder that claims the PyPI name. The full
platform-aware installer (Personal on macOS / Nano elsewhere + MCP and
JSON Tables add-ons) is in progress.
"""

from __future__ import annotations

import platform

from . import __version__

DOCS_URL = "https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/"


def main() -> None:
    system = platform.system() or "unknown"
    print(f"exasol-quickstart {__version__}")
    print()
    print("One command to try Exasol with AI add-ons (MCP Server, JSON Tables).")
    print("The full installer is in progress — this release reserves the name.")
    print()
    print(f"Detected platform: {system} ({platform.machine()})")
    print(f"Plan & docs: {DOCS_URL}")


if __name__ == "__main__":
    main()
