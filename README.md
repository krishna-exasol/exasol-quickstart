<div align="center">

# ⚡ exasol-quickstart

### One command to try **Exasol** with AI add-ons — it installs the right way **for your OS**: the database + an MCP server + JSON Tables, ready in minutes.

[![PyPI](https://img.shields.io/pypi/v/exasol-quickstart?color=3fb950)](https://pypi.org/project/exasol-quickstart/)
[![Python](https://img.shields.io/pypi/pyversions/exasol-quickstart?color=58a6ff)](https://pypi.org/project/exasol-quickstart/)
[![License: MIT](https://img.shields.io/badge/license-MIT-d29922)](LICENSE)

**📦 PyPI: [pypi.org/project/exasol-quickstart](https://pypi.org/project/exasol-quickstart/)** &nbsp;·&nbsp; 💻 [GitHub](https://github.com/krishna-exasol/exasol-quickstart)

</div>

```bash
pipx install exasol-quickstart
exasol-quickstart
```

That's it. The tool **detects your operating system and installs Exasol the right way for it** — no flags, no multi-step setup — then prints the endpoints.

---

## What you get

| Component | Endpoint | What it's for |
|-----------|----------|---------------|
| **Exasol** (database) | `127.0.0.1:8563` · user `sys` / `exasol` | the Exasol SQL engine |
| **MCP Server** | `http://127.0.0.1:4896/mcp` | point Claude / any MCP client here to talk to the DB |
| **JSON Tables** | `exasol-quickstart json-tables …` | ingest JSON and query it as SQL |

Web UI: `https://127.0.0.1:8443`.

## Requirements — only one thing is universal

- **Python 3.9+ with `pipx`** — the only thing you always need. No pipx yet?
  ```bash
  python -m pip install --user pipx
  python -m pipx ensurepath        # then reopen the terminal
  ```

**You do *not* always need Docker.** `exasol-quickstart` picks how Exasol runs based on your OS:

| Your OS | How it installs Exasol | Docker? |
|---------|------------------------|---------|
| **Windows** | Exasol Nano in a container | needs Docker Desktop *(no native Windows engine exists)* |
| **macOS** (Apple Silicon) | Exasol **Personal** — a native VM | **no Docker** *(experimental today)* |
| **Linux** | Exasol Nano container *(native `.run` planned)* | Docker for now |

The container path (Docker) is the most thoroughly **tested** today; the native macOS path is **experimental**. Either way, the command and the result are the same — only the under-the-hood install differs.

## Commands — tailor it to your needs

```bash
exasol-quickstart                      # the full bundle (DB + MCP + JSON Tables)
exasol-quickstart --no-json-tables     # DB + MCP only (faster; skips the Rust build)
exasol-quickstart --dry-run            # show the plan, change nothing
exasol-quickstart --base personal      # force a base: nano-docker | personal | nano-native
exasol-quickstart json-tables --help   # run the JSON Tables CLI
exasol-quickstart --help
```

### Ingest some JSON

```bash
docker cp data.json exasol-quickstart-json-tables:/workspace/data.json
exasol-quickstart json-tables ingest-and-wrap --input /workspace/data.json --name demo
# now query it:  SELECT * FROM "EJT_DEMO_VIEW"."demo";
```

> On the container path, the first run pulls `exasol/nano` + `exasol/mcp-server` and **builds the JSON Tables image once** (it compiles a small Rust engine — a few minutes). Later runs are fast. Stop everything with:
> `docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables`

## Why it's built this way

The Exasol engine is Linux-native, so the most portable, tested path runs it in a **container**; on macOS it can instead use **Exasol Personal**, which runs the database in a native VM (no Docker). MCP and JSON Tables have conflicting `pyexasol` pins, so each runs isolated (separate containers, or separate host envs). Full rationale, decision graph, and pros/cons:

📖 **[The recommended approach](https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/)**

## Status

`0.3.1` — the bare command auto-selects per OS. The **container path** (Nano + MCP + JSON Tables) is **tested end-to-end, including ingest**. The **no-Docker native bases** (Exasol Personal on macOS, Nano `.run` on Linux) are wired in and selected automatically when Docker is absent; the macOS path is **experimental and not yet validated end-to-end**.

## Links

- **PyPI:** <https://pypi.org/project/exasol-quickstart/>
- **GitHub:** <https://github.com/krishna-exasol/exasol-quickstart>
- **Docs (design, decision graph, pros/cons):** <https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/>

## License

[MIT](LICENSE).
