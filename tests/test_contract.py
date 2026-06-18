import pytest

from mcp_tool_contract import (
    CONTENT_TRUST_LEVELS,
    RISK_LEVELS,
    ToolContract,
    get_contract,
    tool,
    tool_annotations,
)


def test_tool_decorator_attaches_contract_without_changing_callable() -> None:
    @tool(risk="external-publication", content_trust="trusted", idempotent=False)
    def publish(): ...

    assert publish() is None
    contract = get_contract(publish)
    assert contract is not None
    assert contract.risk == "external-publication"
    assert contract.content_trust == "trusted"
    assert contract.idempotent is False


def test_get_contract_returns_none_for_undeclared_function() -> None:
    def plain(): ...

    assert get_contract(plain) is None


def test_tool_annotations_empty_for_undeclared_function() -> None:
    def plain(): ...

    assert tool_annotations(plain) == {}


def test_tool_annotations_includes_standard_mcp_hints() -> None:
    @tool(risk="destructive", idempotent=True)
    def delete_everything(): ...

    annotations = tool_annotations(delete_everything)
    assert annotations["readOnlyHint"] is False
    assert annotations["destructiveHint"] is True
    assert annotations["idempotentHint"] is True
    assert annotations["risk_level"] == "destructive"
    assert annotations["content_trust_risk"] == "trusted"


def test_tool_annotations_read_only_hints() -> None:
    @tool(risk="read-only")
    def get_status(): ...

    annotations = tool_annotations(get_status)
    assert annotations["readOnlyHint"] is True
    assert annotations["destructiveHint"] is False


def test_tool_annotations_omits_optional_fields_when_unset() -> None:
    @tool(risk="read-only")
    def get_status(): ...

    annotations = tool_annotations(get_status)
    assert "deprecated_since" not in annotations
    assert "aliases" not in annotations


def test_tool_annotations_includes_deprecated_since_and_aliases_when_set() -> None:
    @tool(risk="read-only", version="2.0.0", deprecated_since="2026-01-01", aliases=["old.name"])
    def get_status(): ...

    annotations = tool_annotations(get_status)
    assert annotations["version"] == "2.0.0"
    assert annotations["deprecated_since"] == "2026-01-01"
    assert annotations["aliases"] == ["old.name"]


def test_invalid_risk_level_rejected_at_decoration_time() -> None:
    with pytest.raises(ValueError, match="risk level"):

        @tool(risk="totally-fine-trust-me")
        def shady(): ...


def test_invalid_content_trust_rejected_at_decoration_time() -> None:
    with pytest.raises(ValueError, match="content_trust"):

        @tool(risk="read-only", content_trust="not-a-real-level")
        def shady(): ...


def test_tool_contract_dataclass_validates_directly() -> None:
    with pytest.raises(ValueError):
        ToolContract(risk="not-a-risk-level")


@pytest.mark.parametrize("risk", sorted(RISK_LEVELS))
def test_every_risk_level_accepted(risk: str) -> None:
    ToolContract(risk=risk)


@pytest.mark.parametrize("content_trust", sorted(CONTENT_TRUST_LEVELS))
def test_every_content_trust_level_accepted(content_trust: str) -> None:
    ToolContract(risk="read-only", content_trust=content_trust)
