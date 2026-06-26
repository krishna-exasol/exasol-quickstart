# exasol-quickstart

**Run Exasol with AI in one command** — a full Exasol analytics database, an LLM-ready MCP server, and JSON-native SQL, set up the right way for your operating system.

[![PyPI](https://img.shields.io/pypi/v/exasol-quickstart?color=1f7a5a)](https://pypi.org/project/exasol-quickstart/)
[![Python](https://img.shields.io/pypi/pyversions/exasol-quickstart?color=3776AB)](https://pypi.org/project/exasol-quickstart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-d29922)](https://github.com/krishna-exasol/exasol-quickstart/blob/main/LICENSE)

## Get started in one line

```bash
pipx run exasol-quickstart
```

Pick the form that fits — **try it** (runs once, nothing installed) or **keep it** (installs the command for repeated use), with either `pipx` or `uv`:

| | with `pipx` | with `uv` |
|---|---|---|
| **Try it once** | `pipx run exasol-quickstart` | `uvx exasol-quickstart` |
| **Keep it** | `pipx install exasol-quickstart && exasol-quickstart` | `uv tool install exasol-quickstart && exasol-quickstart` |

Every form detects your OS, provisions Exasol the right way, and prints the endpoints. No flags, no multi-step setup.

## What you get

```text
exasol-quickstart  ->  three services on one shared network:

+----------------------+   +----------------------+   +----------------------+
|  Exasol  (database)  |   |  MCP server          |   |  JSON Tables         |
|  127.0.0.1:8563      |   |  :4896/mcp           |   |  JSON  ->  SQL       |
+----------------------+   +----------------------+   +----------------------+
```

| Component | Endpoint | Purpose |
|-----------|----------|---------|
| Exasol (database) | `127.0.0.1:8563` — user `sys` / password `exasol` | the Exasol SQL engine |
| MCP Server | `http://127.0.0.1:4896/mcp` | connect Claude / any MCP client to the database |
| JSON Tables | `exasol-quickstart json-tables ...` | ingest JSON and query it as SQL |

Web UI: `https://127.0.0.1:8443`.

## Requirements

The only universal prerequisite is **Python 3.9+ with `pipx`**:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

From there, `exasol-quickstart` chooses how Exasol runs, per platform:

| Operating system | How Exasol runs | Docker |
|------------------|-----------------|--------|
| Windows | Exasol Nano, in a container | required (no native Windows engine exists) |
| macOS (Apple Silicon) | Exasol Personal, in a native VM | not required (experimental) |
| Linux | Exasol Nano, in a container (native install planned) | required for now |

The container path is fully tested today; the macOS native path is experimental and not yet validated end to end.

## Usage

```bash
exasol-quickstart                      # full stack: database + MCP + JSON Tables
exasol-quickstart --no-json-tables     # database + MCP only
exasol-quickstart --dry-run            # print the plan, change nothing
exasol-quickstart --base <name>        # force a base: nano-docker | personal | nano-native
exasol-quickstart json-tables --help   # run the JSON Tables CLI
```

Ingest some JSON:

```bash
docker cp data.json exasol-quickstart-json-tables:/workspace/data.json
exasol-quickstart json-tables ingest-and-wrap --input /workspace/data.json --name demo
```

Stop and remove everything:

```bash
docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables
```

## How it works

`exasol-quickstart` is a single front-door command that detects the platform and assembles the stack. With Docker, Exasol Nano, the official `exasol/mcp-server` image, and a JSON Tables sidecar run as containers on a shared network (tested end to end, including ingest). Without Docker, macOS uses Exasol Personal in a native VM and Linux uses a native Nano install (planned), with the add-ons as isolated host environments.

MCP Server and JSON Tables have incompatible `pyexasol` requirements, so each runs in isolation — a separate container or host environment — never a shared Python environment.

## Links

- PyPI: https://pypi.org/project/exasol-quickstart/
- GitHub: https://github.com/krishna-exasol/exasol-quickstart

## License

MIT
