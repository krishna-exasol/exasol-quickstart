<div align="center">

# exasol-quickstart

**Run Exasol with AI add-ons in one command** — the database, an MCP server, and JSON Tables, set up the right way for your operating system.

[![PyPI](https://img.shields.io/pypi/v/exasol-quickstart?color=3fb950)](https://pypi.org/project/exasol-quickstart/)
[![Python](https://img.shields.io/pypi/pyversions/exasol-quickstart?color=58a6ff)](https://pypi.org/project/exasol-quickstart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-d29922)](LICENSE)

[PyPI](https://pypi.org/project/exasol-quickstart/) · [GitHub](https://github.com/krishna-exasol/exasol-quickstart)

</div>

---

## Quickstart

**To try it** — runs once, nothing left installed:

```bash
pipx run exasol-quickstart      # with pipx
uvx exasol-quickstart           # with uv
```

**To keep it** — installs the command so you can run it again later:

```bash
pipx install exasol-quickstart && exasol-quickstart      # with pipx
uv tool install exasol-quickstart && exasol-quickstart   # with uv
```

Either form detects your operating system, provisions Exasol the appropriate way, and prints the connection endpoints. No flags, no multi-step setup.

## What you get

| Component | Endpoint | Purpose |
|-----------|----------|---------|
| **Exasol** (database) | `127.0.0.1:8563` — user `sys` / password `exasol` | the Exasol SQL engine |
| **MCP Server** | `http://127.0.0.1:4896/mcp` | connect an LLM / MCP client to the database |
| **JSON Tables** | `exasol-quickstart json-tables …` | ingest JSON and query it as SQL |

Web UI: `https://127.0.0.1:8443`.

## Requirements

The only universal prerequisite is **Python 3.9+ with `pipx`**:

```bash
python -m pip install --user pipx
python -m pipx ensurepath        # then reopen the terminal
```

Beyond that, `exasol-quickstart` chooses how Exasol runs based on your platform:

| Operating system | How Exasol runs | Docker |
|------------------|-----------------|--------|
| **Windows** | Exasol Nano, in a container | required *(no native Windows engine exists)* |
| **macOS** (Apple Silicon) | Exasol Personal, in a native VM | not required *(experimental)* |
| **Linux** | Exasol Nano, in a container *(native install planned)* | required for now |

The container-based path is fully tested today; the macOS native path is experimental and not yet validated end to end.

## Usage

```bash
exasol-quickstart                      # full stack: database + MCP + JSON Tables
exasol-quickstart --no-json-tables     # database + MCP only
exasol-quickstart --dry-run            # print the plan without making changes
exasol-quickstart --base <name>        # force a base: nano-docker | personal | nano-native
exasol-quickstart json-tables --help   # run the JSON Tables CLI
```

Stop and remove the stack:

```bash
docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables
```

## Ingesting JSON

```bash
docker cp data.json exasol-quickstart-json-tables:/workspace/data.json
exasol-quickstart json-tables ingest-and-wrap --input /workspace/data.json --name demo
# then query it:  SELECT * FROM "EJT_DEMO_VIEW"."demo";
```

On the container path, the first run pulls the `exasol/nano` and `exasol/mcp-server` images and builds the JSON Tables image once (it compiles a small Rust engine — a few minutes). Subsequent runs are fast.

## How it works

`exasol-quickstart` is a single front-door command that detects the platform and assembles the stack accordingly:

- **With Docker** — Exasol Nano (database), the official `exasol/mcp-server` image, and a JSON Tables sidecar run as containers on a shared network. This path is tested end to end, including ingest.
- **Without Docker** — on macOS it uses Exasol Personal (a native VM); on Linux, a native Nano install (planned). The add-ons run as isolated host environments.

MCP Server and JSON Tables have incompatible `pyexasol` requirements, so each runs in isolation — a separate container, or a separate host environment — never a shared Python environment.

## Status

`0.3.x` — the container path (Nano + MCP + JSON Tables) is tested end to end, including ingest. The no-Docker native bases are selected automatically when Docker is absent; the macOS path is experimental and not yet validated.

## License

[MIT](LICENSE)
