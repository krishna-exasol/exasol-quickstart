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

> **Status (`0.2.0`):** the bare command stands up **Nano + MCP + JSON Tables** via Docker
> on any OS — tested end-to-end. Next: **no-Docker native bases per OS** (Exasol Personal
> on macOS, Nano `.run` on Linux), selected automatically — same bare command.

## Roadmap — same command, smarter under the hood

| OS | Planned best base | Add-ons | Docker? | Status |
|----|-------------------|---------|---------|--------|
| Windows / any with Docker | Exasol Nano (Docker) | sidecar containers | Yes | **ships today** |
| macOS (Apple Silicon) | Exasol Personal (local VM) | host: MCP + JSON Tables | No | roadmap |
| Linux | Exasol Nano (native `.run`) | host: MCP + JSON Tables | No | roadmap |

Full design, decision graph, pros/cons, and requirements:
<https://krishna-exasol.github.io/bundle-installation-methods/case-studies/recommended-approach/>

## License

[MIT](LICENSE).
