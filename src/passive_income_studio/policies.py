from __future__ import annotations

import re
from dataclasses import dataclass

from passive_income_studio.schemas import ApprovalStatus, Decision, ExperimentCard, RiskFlag


FORBIDDEN_CLAIM_PATTERNS = [
    r"\bguaranteed\b",
    r"\brisk[- ]?free\b",
    r"\breplace your job\b",
    r"\bearn\s+\$?\d+[,\d]*(?:\.\d+)?\s*(?:/|per)?\s*(?:day|week|month|year)\b",
    r"\bmake\s+\$?\d+[,\d]*(?:\.\d+)?\s*(?:/|per)?\s*(?:day|week|month|year)\b",
    r"\bset and forget\b",
]

IP_RISK_TERMS = [
    "disney",
    "marvel",
    "star wars",
    "taylor swift",
    "nike",
    "apple",
    "pokemon",
    "harry potter",
    "in the style of",
]

REGULATED_TERMS = [
    "investment advice",
    "stock recommendation",
    "legal advice",
    "medical advice",
    "tax advice",
]


@dataclass(frozen=True)
class SafetyGateResult:
    status: ApprovalStatus
    decision: Decision
    flags: list[RiskFlag]


class SafetyGateEngine:
    """Deterministic policy checks for no-spend v1."""

    def evaluate_text(self, text: str) -> list[RiskFlag]:
        lowered = text.lower()
        flags: list[RiskFlag] = []

        for pattern in FORBIDDEN_CLAIM_PATTERNS:
            if re.search(pattern, lowered):
                flags.append(
                    RiskFlag(
                        category="claims",
                        severity="blocking",
                        message="Unsupported earnings or passive-income claim detected.",
                        gate="Claims Gate",
                    )
                )
                break

        for term in IP_RISK_TERMS:
            if term in lowered:
                flags.append(
                    RiskFlag(
                        category="ip",
                        severity="blocking",
                        message=f"Protected brand, character, celebrity, or style reference detected: {term}.",
                        gate="IP Gate",
                    )
                )
                break

        for term in REGULATED_TERMS:
            if term in lowered:
                flags.append(
                    RiskFlag(
                        category="regulated",
                        severity="blocking",
                        message=f"Regulated-topic language detected: {term}.",
                        gate="Claims Gate",
                    )
                )
                break

        if "affiliate" in lowered and "disclosure" not in lowered:
            flags.append(
                RiskFlag(
                    category="disclosure",
                    severity="medium",
                    message="Affiliate language needs a clear disclosure near the recommendation.",
                    gate="Disclosure Gate",
                )
            )

        return flags

    def evaluate_card(self, card: ExperimentCard) -> SafetyGateResult:
        corpus = " ".join(
            [
                card.hypothesis,
                card.audience,
                card.buyer_job,
                *[deliverable.summary for deliverable in card.deliverables],
            ]
        )
        flags = [*card.risk_flags, *self.evaluate_text(corpus)]

        if card.metrics.costs > 0:
            flags.append(
                RiskFlag(
                    category="spend",
                    severity="blocking",
                    message="No-spend v1 cannot incur costs without explicit approval.",
                    gate="Spend Gate",
                )
            )

        if any(flag.severity == "blocking" for flag in flags):
            return SafetyGateResult(ApprovalStatus.quarantined, Decision.quarantine, flags)

        return SafetyGateResult(ApprovalStatus.review_required, Decision.launch_review, flags)

    def enforce(self, card: ExperimentCard) -> ExperimentCard:
        result = self.evaluate_card(card)
        return card.model_copy(
            update={
                "risk_flags": result.flags,
                "approval_status": result.status,
                "decision": result.decision,
            }
        )

