<div align="center">

# ⚡ exasol-quickstart

### One command to try **Exasol** with AI add-ons — the database + an MCP server + JSON Tables, ready in minutes.

[![PyPI](https://img.shields.io/pypi/v/exasol-quickstart?color=3fb950)](https://pypi.org/project/exasol-quickstart/)
[![Python](https://img.shields.io/pypi/pyversions/exasol-quickstart?color=58a6ff)](https://pypi.org/project/exasol-quickstart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-d29922)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-recommended%20approach-bc8cff)](https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/)

**📦 PyPI: [pypi.org/project/exasol-quickstart](https://pypi.org/project/exasol-quickstart/)** &nbsp;·&nbsp; 💻 [GitHub](https://github.com/krishna-exasol/exasol-quickstart) &nbsp;·&nbsp; 📖 [Docs](https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/)

</div>

```bash
pipx install exasol-quickstart
exasol-quickstart
```

That's it. On any machine with **Docker**, the bare command stands up the full stack and prints the endpoints — no flags, no multi-step setup.

---

## What you get

Three containers on a shared Docker network:

| Component | Endpoint | What it's for |
|-----------|----------|---------------|
| **Exasol Nano** (database) | `127.0.0.1:8563` · user `sys` / `exasol` | the Exasol SQL engine |
| **MCP Server** | `http://127.0.0.1:4896/mcp` | point Claude / any MCP client here to talk to the DB |
| **JSON Tables** | `exasol-quickstart json-tables …` | ingest JSON and query it as SQL |

Web UI: `https://127.0.0.1:8443`.

## Requirements

- **Docker** installed and running (Docker Desktop on Windows/macOS, or Docker/Podman on Linux).
- **Python 3.9+** with **`pipx`**. No pipx yet?
  ```bash
  python -m pip install --user pipx
  python -m pipx ensurepath        # then reopen the terminal
  ```

That's all the host needs — the database, MCP, Python, and Rust all live inside the containers.

## Commands

```bash
exasol-quickstart                      # bring up the full bundle (DB + MCP + JSON Tables)
exasol-quickstart --dry-run            # show the plan, change nothing
exasol-quickstart --no-json-tables     # DB + MCP only (faster; skips the Rust build)
exasol-quickstart json-tables --help   # run the JSON Tables CLI inside its container
exasol-quickstart --help

# stop / clean up
docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables
```

### Ingest some JSON

```bash
# put a file in the workspace volume, then ingest + wrap it as SQL views
docker cp data.json exasol-quickstart-json-tables:/workspace/data.json
exasol-quickstart json-tables ingest-and-wrap --input /workspace/data.json --name demo
# now query it: SELECT * FROM "EJT_DEMO_VIEW"."demo";
```

> The first run pulls `exasol/nano` + `exasol/mcp-server` and **builds the JSON Tables image once** (it compiles a small Rust engine — a few minutes). Subsequent runs are fast.

## How it works — auto base selection

The command always means *"give me Exasol + AI, the best way for this machine."* It picks the base automatically:

| Situation | Base used | Add-ons | Status |
|-----------|-----------|---------|--------|
| Any OS **with Docker** | Exasol Nano (Docker) | MCP + JSON Tables as **sidecar containers** | ✅ **tested** |
| macOS (Apple Silicon), **no Docker** | Exasol **Personal** (local VM) | MCP (`pipx`) + JSON Tables (venv) on the host | 🧪 experimental |
| Linux, **no Docker** | Exasol Nano (native `.run`) | host processes | 🛣️ roadmap |

Override anytime: `exasol-quickstart --base nano-docker | personal | nano-native`.

Why two containers for MCP instead of one Nano image? The published Nano image doesn't expose its "stack" system yet, and MCP and JSON Tables have conflicting `pyexasol` pins — so each runs in its own container on a shared network. Full rationale, decision graph, and pros/cons:

📖 **[The recommended approach](https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/)**

## Status

`0.3.0` — the bare command brings up **Nano + MCP + JSON Tables via Docker** on any OS (tested end-to-end, including ingest). The no-Docker native bases (Personal on macOS, Nano `.run` on Linux) are selected automatically when Docker is absent; the macOS path is **experimental and not yet validated end-to-end**.

## Links

- **PyPI:** <https://pypi.org/project/exasol-quickstart/>
- **GitHub:** <https://github.com/krishna-exasol/exasol-quickstart>
- **Docs (design, decision graph, pros/cons):** <https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/>

## License

[MIT](LICENSE).
