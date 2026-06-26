<h1 align="center">⚡ exasol-quickstart</h1>

<p align="center"><b>Run Exasol with AI — in one command.</b></p>

<p align="center">A full Exasol analytics database, an LLM-ready MCP server, and JSON-native SQL — set up the right way for your OS, in minutes.</p>

<p align="center">
  <a href="https://pypi.org/project/exasol-quickstart/"><img src="https://img.shields.io/pypi/v/exasol-quickstart?style=for-the-badge&color=1f7a5a&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://pypi.org/project/exasol-quickstart/"><img src="https://img.shields.io/pypi/pyversions/exasol-quickstart?style=for-the-badge&color=3776AB&logo=python&logoColor=white" alt="Python"></a>
  <img src="https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-555?style=for-the-badge" alt="Platforms">
  <img src="https://img.shields.io/badge/license-MIT-d29922?style=for-the-badge" alt="License">
</p>

---

## ⚡ Get started

**▶️ Try it** — runs once, nothing installed:

```bash
pipx run exasol-quickstart
```

…or, if you prefer [uv](https://docs.astral.sh/uv/):

```bash
uvx exasol-quickstart
```

**📌 Keep it** — installs the command so you can run it again later:

```bash
pipx install exasol-quickstart && exasol-quickstart
```

…or, with uv:

```bash
uv tool install exasol-quickstart && exasol-quickstart
```

Every form detects your OS, provisions Exasol the right way, and prints the endpoints. **No flags. No multi-step setup.**

## 🎁 What you get

```text
exasol-quickstart  ->  three services on one shared network:

+----------------------+   +----------------------+   +----------------------+
|  Exasol  (database)  |   |  MCP server          |   |  JSON Tables         |
|  127.0.0.1:8563      |   |  :4896/mcp           |   |  JSON  ->  SQL       |
+----------------------+   +----------------------+   +----------------------+
```

| Component | Endpoint | Purpose |
|-----------|----------|---------|
| 🗄️ **Exasol** (database) | `127.0.0.1:8563` — `sys` / `exasol` | the Exasol SQL engine |
| 🤖 **MCP Server** | `http://127.0.0.1:4896/mcp` | connect Claude / any MCP client to the database |
| 📦 **JSON Tables** | `exasol-quickstart json-tables ...` | ingest JSON and query it as SQL |

Web UI: `https://127.0.0.1:8443`

## ✅ Requirements

The only thing you **always** need is **Python 3.9+ with `pipx`**:

```bash
python -m pip install --user pipx
python -m pipx ensurepath        # then reopen the terminal
```

From there, `exasol-quickstart` picks **how** Exasol runs, per platform:

| Operating system | How Exasol runs | Docker |
|------------------|-----------------|--------|
| 🪟 **Windows** | Exasol Nano, in a container | required *(no native Windows engine exists)* |
| 🍎 **macOS** (Apple Silicon) | Exasol Personal, in a native VM | not required *(experimental)* |
| 🐧 **Linux** | Exasol Nano, in a container *(native install planned)* | required for now |

> The container path is **fully tested** today; the macOS native path is **experimental** and not yet validated end to end.

## 🛠️ Usage

```bash
exasol-quickstart                      # full stack: database + MCP + JSON Tables
exasol-quickstart --no-json-tables     # database + MCP only
exasol-quickstart --dry-run            # print the plan, change nothing
exasol-quickstart --base <name>        # force a base: nano-docker | personal | nano-native
exasol-quickstart json-tables --help   # run the JSON Tables CLI
```

**Ingest some JSON:**

```bash
docker cp data.json exasol-quickstart-json-tables:/workspace/data.json
exasol-quickstart json-tables ingest-and-wrap --input /workspace/data.json --name demo
# then query it:  SELECT * FROM "EJT_DEMO_VIEW"."demo";
```

**Stop &amp; remove everything:**

```bash
docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables
```

## 🧩 How it works

`exasol-quickstart` is a single front-door command that detects the platform and assembles the stack:

- **With Docker** — Exasol Nano (database), the official `exasol/mcp-server` image, and a JSON Tables sidecar run as containers on a shared network. Tested end to end, including ingest.
- **Without Docker** — macOS uses Exasol Personal (a native VM); Linux uses a native Nano install (planned). The add-ons run as isolated host environments.

MCP Server and JSON Tables have incompatible `pyexasol` requirements, so each runs in isolation — a separate container, or a separate host environment — never a shared Python environment.

---

<p align="center">
  <b><a href="https://github.com/krishna-exasol/exasol-quickstart">GitHub</a> &nbsp;•&nbsp; <a href="https://pypi.org/project/exasol-quickstart/">PyPI</a></b><br>
  <sub>Made to make trying Exasol effortless &nbsp;•&nbsp; MIT</sub>
</p>
