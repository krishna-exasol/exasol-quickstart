# exasol-quickstart

**One command to try Exasol with AI add-ons** — a base Exasol database plus the
**MCP Server** (LLM/agent access) and, optionally, **JSON Tables** (JSON → SQL),
chosen automatically for your operating system.

> **Status:** `0.0.1` is a name-reservation placeholder. The full platform-aware
> installer is in progress.

## Planned usage

```bash
pipx install exasol-quickstart
exasol-quickstart                 # base + MCP server
exasol-quickstart --with json-tables   # base + MCP + JSON Tables
```

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
