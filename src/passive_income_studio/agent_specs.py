from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    purpose: str
    output_contract: str
    may_do: tuple[str, ...]
    must_not_do: tuple[str, ...]


HARD_STOPS = (
    "publish externally",
    "spend money",
    "send outreach",
    "upload products",
    "create accounts",
    "change platform settings",
)


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        name="Opportunity Scout",
        purpose="Find micro-niches, buyer jobs, keywords, competitor signals, and pricing patterns.",
        output_contract="ranked niche options with demand signal, competition note, and validation method",
        may_do=("research", "summarize", "score opportunities"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Product Strategist",
        purpose="Choose one product concept and define promise, bundle contents, price, and validation criteria.",
        output_contract="selected concept with audience, buyer job, product type, price, and hypothesis",
        may_do=("prioritize", "price", "define product scope"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Asset Builder",
        purpose="Draft the product files and practical user-facing content.",
        output_contract="deliverables with summaries and provenance notes",
        may_do=("draft", "outline", "package product content"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Design/Packaging Agent",
        purpose="Create naming, cover direction, preview image brief, and file organization.",
        output_contract="brand-safe package metadata and preview briefs",
        may_do=("name", "structure", "prepare visual briefs"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Compliance/IP Agent",
        purpose="Review claims, copyright, trademark, disclosure, platform, outreach, and spend risk.",
        output_contract="risk flags and required approval gates",
        may_do=("classify risk", "block unsafe content", "request review"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="QA Agent",
        purpose="Verify product usefulness, completeness, consistency, links, and launch readiness.",
        output_contract="QA notes with pass/fail checks",
        may_do=("verify", "flag missing pieces", "recommend fixes"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Launch Prep Agent",
        purpose="Prepare Gumroad/Payhip listing copy, tags, FAQ, refund/support text, and publish checklist.",
        output_contract="storefront draft and manual launch checklist",
        may_do=("draft listing", "draft FAQ", "prepare checklist"),
        must_not_do=HARD_STOPS,
    ),
    AgentSpec(
        name="Analytics Agent",
        purpose="After manual launch, ingest metrics and recommend iterate, scale, stop, or quarantine.",
        output_contract="metric summary and decision recommendation",
        may_do=("read metrics", "recommend next action", "update learning ledger"),
        must_not_do=HARD_STOPS,
    ),
)


def build_openai_agent_definitions():
    """Return OpenAI Agents SDK Agent objects when the SDK is installed.

    The deterministic local orchestrator is the default no-side-effect path. This
    adapter exists so the same specialist contracts can be used for future live
    SDK runs without changing the business schemas.
    """

    try:
        from agents import Agent
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError("Install openai-agents to build live SDK agents.") from exc

    return [
        Agent(
            name=spec.name,
            instructions=(
                f"Purpose: {spec.purpose}\n"
                f"Output contract: {spec.output_contract}\n"
                f"You may: {', '.join(spec.may_do)}.\n"
                f"You must not: {', '.join(spec.must_not_do)}.\n"
                "Return structured, audit-friendly content only."
            ),
        )
        for spec in AGENT_SPECS
    ]

