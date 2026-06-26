# exasol-quickstart

**One command to try Exasol with AI add-ons** — a base Exasol database plus the
**MCP Server** (LLM/agent access) and, optionally, **JSON Tables** (JSON → SQL),
chosen automatically for your operating system.

> **Status (`0.1.1`):** brings up **Exasol Nano (database) + the official Exasol MCP
> server image as a sidecar**, via Docker, on any OS — tested end-to-end. The per-OS
> native bases (Personal on macOS, Nano `.run` on Linux) and JSON Tables are next.

## Usage

```bash
# from PyPI (reserved name) — or the latest from git:
pipx install git+https://github.com/krishna-exasol/exasol-quickstart.git

exasol-quickstart --base nano-docker        # Exasol Nano + MCP (works today, any OS w/ Docker)
exasol-quickstart --dry-run                 # show the plan without doing anything
exasol-quickstart --help
```

After it comes up: database on `127.0.0.1:8563` (`sys`/`exasol`), MCP at
`http://127.0.0.1:4896/mcp`. Stop with `docker rm -f exasol-quickstart`.

## How it will work (per OS)

| OS | Base | Add-ons | Docker? |
|----|------|---------|---------|
| macOS (Apple Silicon) | Exasol Personal (local VM) | host: MCP + JSON Tables | No |
| Linux | Exasol Nano (native `.run`) | Nano stacks | No |
| Windows | Exasol Nano (Docker) | Nano stacks | Yes |

Full design, decision graph, pros/cons, and requirements:
<https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/>

## License

[MIT](LICENSE).
