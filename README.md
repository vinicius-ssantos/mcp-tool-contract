# mcp-tool-contract

Shared taxonomies and a `@tool` decorator that let an MCP tool self-declare
the facts about itself that only its author knows for certain: risk level,
content trustworthiness, idempotency, and lifecycle (version/deprecation).

This implements Layer 1 ("Facts") of
[ADR 0016](https://github.com/vinicius-ssantos/central-mcp-gateway/blob/main/docs/adr/0016-upstream-declared-tool-contract.md)
in `central-mcp-gateway`. Every upstream MCP service the gateway aggregates is
owned by the same team, so instead of the gateway guessing these facts from a
tool's name/description (or requiring them to be re-declared by hand in a
separate catalog file), the tool's own definition is the single source of
truth and the gateway reads it from `tools/list`.

## Install

```bash
pip install mcp-tool-contract
```

or with `uv`:

```bash
uv add mcp-tool-contract
```

## Usage

```python
from mcp_tool_contract import tool, tool_annotations

@tool(
    risk="external-publication",   # one of RISK_LEVELS
    content_trust="trusted",       # one of CONTENT_TRUST_LEVELS
    idempotent=False,
    version="2.1.0",
)
def post_update(...):
    ...
```

When your MCP server framework builds the `tools/list` response for a tool,
merge `tool_annotations(post_update)` into that tool's `annotations` dict
alongside its real `inputSchema` and `description` (which this package does
not touch — your framework already derives those from the function
signature/docstring).

`tool_annotations()` returns `{}` for an undeclared function, so adoption can
be incremental: undecorated tools simply fall back to the gateway's existing
name/description heuristic, exactly as before.

## Taxonomies

- `RISK_LEVELS` / `RISK_LEVEL_ORDER` — `read-only` < `low-risk-write` <
  `high-risk-write` < `external-publication` < `paid-operation` <
  `destructive`.
- `CONTENT_TRUST_LEVELS` — `trusted`, `untrusted`, `sensitive`,
  `prompt-injection-prone`. Orthogonal to risk: a read-only tool can still
  return untrusted or adversarial content.

An unrecognised value for either field raises `ValueError` at decoration
time — a typo in the upstream fails that upstream's own CI, instead of
silently falling back to the gateway's heuristic.

## Trust boundary

The gateway remains the single point of control (ADR 0001). A declared fact
is the *default*; the gateway's static catalog may still veto or override any
tool's effective risk, content-trust, or schema (ADR 0016 Layer 3), and an
anti-downgrade check flags any tool whose effective risk or content-trust
weakens between discovery cycles without a recorded catalog override.

## Release

Bump `version` in `pyproject.toml`, then tag and push:

```bash
git tag v0.2.0
git push origin v0.2.0
```

`.github/workflows/publish.yml` builds and publishes the tagged version to
PyPI.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```
