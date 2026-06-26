# exasol-quickstart

**One command to try Exasol with AI add-ons** — a base Exasol database plus the
**MCP Server** (LLM/agent access) and **JSON Tables** (JSON → SQL).

## Usage

```bash
pipx install exasol-quickstart
exasol-quickstart                 # brings up the full bundle (needs Docker running)
```

That's it. On any OS with Docker it starts three containers on a shared network:

- **Exasol Nano** — the database, `127.0.0.1:8563` (`sys` / `exasol`)
- **MCP Server** — `http://127.0.0.1:4896/mcp` (point your LLM / MCP client here)
- **JSON Tables** — built once from source, run via `exasol-quickstart json-tables …`

### Other commands

```bash
exasol-quickstart --dry-run            # show the plan, change nothing
exasol-quickstart --no-json-tables     # DB + MCP only (skip JSON Tables)
exasol-quickstart json-tables --help   # run the JSON Tables CLI in its container
docker rm -f exasol-quickstart-db exasol-quickstart-mcp exasol-quickstart-json-tables   # stop
```

> **Status (`0.3.0`):** the bare command **auto-selects the base** — Nano + Docker when
> Docker is available (tested end-to-end: DB + MCP + JSON Tables incl. ingest), or the
> **OS-native no-Docker base** when it isn't (Exasol Personal on macOS / Nano `.run` on
> Linux — *experimental, not yet validated end-to-end*). Same bare command everywhere.

## Auto base selection — same command, smarter under the hood

| Situation | Base used | Add-ons | Status |
|-----------|-----------|---------|--------|
| Any OS **with Docker** | Exasol Nano (Docker) | sidecar containers | **tested** |
| macOS (Apple Silicon), **no Docker** | Exasol Personal (local VM) | host: MCP (pipx) + JSON Tables (venv) | experimental |
| Linux, **no Docker** | Exasol Nano (native `.run`) | host | roadmap |

Force a specific base with `--base nano-docker|personal|nano-native`.

Full design, decision graph, pros/cons, and requirements:
<https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/>

## License

[MIT](LICENSE).
