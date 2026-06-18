"""Shared tool-contract taxonomies and decorator (ADR 0016).

central-mcp-gateway aggregates tools from several upstream MCP services that we
own. Facts about what a tool *is* and *does* — risk level, content
trustworthiness, idempotency, version — are known with certainty by the
upstream that implements the tool, yet historically the gateway either
guessed them from the tool's name/description or required them to be
re-declared by hand in a separate catalog file. That duplication drifts.

This package lets an upstream tool self-declare those facts once, at the
point where the tool is defined, via the ``@tool`` decorator. The facts are
exposed as ``tools/list`` annotations that central-mcp-gateway reads as the
default value for each field, falling back to its own heuristics only for
tools that declare nothing.

Usage in an upstream MCP server::

    from mcp_tool_contract import tool, tool_annotations

    @tool(risk="external-publication", content_trust="trusted", idempotent=False)
    def post_update(...): ...

    # When building the tools/list response for this tool:
    annotations = tool_annotations(post_update)

See docs/adr/0016-upstream-declared-tool-contract.md in central-mcp-gateway
for the full design (the gateway remains the trust boundary: it may always
veto or override a declared fact via its static catalog — ADR 0016 Layer 3).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "RISK_LEVELS",
    "RISK_LEVEL_ORDER",
    "CONTENT_TRUST_LEVELS",
    "ToolContract",
    "tool",
    "get_contract",
    "tool_annotations",
]

# Valid risk levels, in ascending order of side-effect impact. Mirrors
# central_mcp_gateway.tools.RISK_LEVELS — the two must not diverge; this
# package is the canonical source once the gateway migrates to import it.
RISK_LEVELS = frozenset(
    {
        "read-only",
        "low-risk-write",
        "high-risk-write",
        "external-publication",
        "paid-operation",
        "destructive",
    }
)

RISK_LEVEL_ORDER = (
    "read-only",
    "low-risk-write",
    "high-risk-write",
    "external-publication",
    "paid-operation",
    "destructive",
)

# Trustworthiness of a tool's *response* content. Orthogonal to risk_level: a
# read-only tool can still return untrusted or adversarial content (e.g. a
# tool that fetches a web page).
CONTENT_TRUST_LEVELS = frozenset(
    {
        "trusted",
        "untrusted",
        "sensitive",
        "prompt-injection-prone",
    }
)

# Annotation keys central-mcp-gateway's discovery reads from tools/list, in
# addition to the three standard MCP hints (readOnlyHint, destructiveHint,
# idempotentHint), which cannot alone express a 6-level risk taxonomy or a
# 4-level content-trust taxonomy.
ANNOTATION_RISK_LEVEL = "risk_level"
ANNOTATION_CONTENT_TRUST_RISK = "content_trust_risk"
ANNOTATION_VERSION = "version"
ANNOTATION_DEPRECATED_SINCE = "deprecated_since"
ANNOTATION_ALIASES = "aliases"

_CONTRACT_ATTR = "__mcp_tool_contract__"


@dataclass(frozen=True)
class ToolContract:
    """A tool's self-declared Layer-1 facts (ADR 0016)."""

    risk: str
    content_trust: str = "trusted"
    idempotent: bool = False
    version: str = "1.0.0"
    deprecated_since: str | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.risk not in RISK_LEVELS:
            raise ValueError(
                f"Unknown risk level {self.risk!r}; must be one of {sorted(RISK_LEVELS)}"
            )
        if self.content_trust not in CONTENT_TRUST_LEVELS:
            raise ValueError(
                f"Unknown content_trust {self.content_trust!r}; "
                f"must be one of {sorted(CONTENT_TRUST_LEVELS)}"
            )

    def to_annotations(self) -> dict[str, Any]:
        """Render this contract as MCP tools/list annotation fields."""
        annotations: dict[str, Any] = {
            "readOnlyHint": self.risk == "read-only",
            "destructiveHint": self.risk == "destructive",
            "idempotentHint": self.idempotent,
            ANNOTATION_RISK_LEVEL: self.risk,
            ANNOTATION_CONTENT_TRUST_RISK: self.content_trust,
            ANNOTATION_VERSION: self.version,
        }
        if self.deprecated_since is not None:
            annotations[ANNOTATION_DEPRECATED_SINCE] = self.deprecated_since
        if self.aliases:
            annotations[ANNOTATION_ALIASES] = list(self.aliases)
        return annotations


def tool(
    *,
    risk: str,
    content_trust: str = "trusted",
    idempotent: bool = False,
    version: str = "1.0.0",
    deprecated_since: str | None = None,
    aliases: Sequence[str] = (),
):
    """Decorator: self-declare a tool's Layer-1 facts.

    Raises ValueError immediately (at import time, not at gateway-discovery
    time) if ``risk`` or ``content_trust`` is not a recognised taxonomy value
    — a typo here must fail the upstream's own CI, not silently fall back to
    the gateway's heuristic.
    """
    contract = ToolContract(
        risk=risk,
        content_trust=content_trust,
        idempotent=idempotent,
        version=version,
        deprecated_since=deprecated_since,
        aliases=tuple(aliases),
    )

    def decorator(func):
        setattr(func, _CONTRACT_ATTR, contract)
        return func

    return decorator


def get_contract(func: Any) -> ToolContract | None:
    """Return the ToolContract attached to func by @tool, or None if undeclared."""
    return getattr(func, _CONTRACT_ATTR, None)


def tool_annotations(func: Any) -> dict[str, Any]:
    """Return the tools/list annotation fields for func, or {} if undeclared.

    Merge this into whatever annotations dict the upstream's MCP framework
    builds for the tool, alongside its real inputSchema and description.
    """
    contract = get_contract(func)
    return contract.to_annotations() if contract is not None else {}
