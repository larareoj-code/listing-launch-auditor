from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ApprovalStatus(str, Enum):
    draft_internal = "draft_internal"
    review_required = "review_required"
    approved_for_manual_launch = "approved_for_manual_launch"
    blocked = "blocked"
    quarantined = "quarantined"


class Decision(str, Enum):
    draft = "draft"
    launch_review = "launch_review"
    iterate = "iterate"
    scale = "scale"
    stop = "stop"
    quarantine = "quarantine"


class Platform(str, Enum):
    gumroad = "Gumroad"
    payhip = "Payhip"
    kofi = "Ko-fi"
    fourthwall = "Fourthwall"
    buy_me_a_coffee = "Buy Me a Coffee"


class ProductType(str, Enum):
    template = "template"
    guide = "guide"
    planner = "planner"
    prompt_pack = "prompt_pack"
    checklist = "checklist"
    swipe_file = "swipe_file"
    resource_bundle = "resource_bundle"


class RiskFlag(BaseModel):
    category: Literal[
        "claims",
        "ip",
        "platform",
        "spend",
        "outreach",
        "regulated",
        "quality",
        "disclosure",
    ]
    severity: Literal["low", "medium", "high", "blocking"]
    message: str = Field(min_length=5)
    gate: str = Field(min_length=3)


class Metrics(BaseModel):
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    costs: float = 0.0
    refund_rate: float = 0.0
    notes: list[str] = Field(default_factory=list)

    @property
    def net_profit(self) -> float:
        return self.revenue - self.costs


class Deliverable(BaseModel):
    name: str = Field(min_length=3)
    kind: Literal["product_file", "listing_copy", "preview_image", "checklist", "faq", "policy_note"]
    format: str = Field(min_length=2)
    summary: str = Field(min_length=10)
    provenance: list[str] = Field(default_factory=list)

    @field_validator("provenance")
    @classmethod
    def provenance_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("every deliverable needs IP/provenance notes")
        return value


class ExperimentCard(BaseModel):
    hypothesis: str = Field(min_length=20)
    audience: str = Field(min_length=5)
    buyer_job: str = Field(min_length=10)
    product_type: ProductType
    deliverables: list[Deliverable] = Field(min_length=1)
    price: float = Field(ge=0, le=99)
    platform: Platform
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.draft_internal
    metrics: Metrics = Field(default_factory=Metrics)
    decision: Decision = Decision.draft

    @model_validator(mode="after")
    def block_external_action_states(self) -> "ExperimentCard":
        blocking = [flag for flag in self.risk_flags if flag.severity == "blocking"]
        if blocking and self.approval_status not in {ApprovalStatus.blocked, ApprovalStatus.quarantined}:
            raise ValueError("blocking risks require blocked or quarantined approval status")
        if self.decision in {Decision.scale, Decision.iterate} and self.approval_status == ApprovalStatus.draft_internal:
            raise ValueError("non-draft decisions require review context")
        return self


class AgentResult(BaseModel):
    agent_name: str
    summary: str
    artifacts: dict[str, object] = Field(default_factory=dict)
    risk_flags: list[RiskFlag] = Field(default_factory=list)


class LaunchPackage(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    brand_name: str
    experiment: ExperimentCard
    agent_results: list[AgentResult]
    storefront_listing: dict[str, object]
    publish_checklist: list[str]
    approval_required_before: list[str]
    learning_ledger_event: dict[str, object]

    @field_validator("approval_required_before")
    @classmethod
    def approvals_must_exist(cls, value: list[str]) -> list[str]:
        required = {"publishing", "spend", "outreach", "platform changes"}
        if not required.issubset(set(value)):
            raise ValueError("launch package must preserve hard approval gates")
        return value


class AppExperiment(BaseModel):
    id: str = Field(min_length=3)
    app_type: str = Field(min_length=3)
    audience: str = Field(min_length=3)
    buyer_job: str = Field(min_length=10)
    hypothesis: str = Field(min_length=20)
    acquisition_channel: str = Field(min_length=3)
    free_value: str = Field(min_length=10)
    paid_value: str = Field(min_length=10)
    price: str = Field(min_length=2)
    status: Literal["idea", "building", "live", "paused", "stopped"] = "idea"
    metrics: dict[str, float | int] = Field(default_factory=dict)
    decision: Literal["build", "monitor", "iterate", "scale", "stop"] = "build"


class ListingAuditRequest(BaseModel):
    platform: Platform
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=20, max_length=10000)
    price: float = Field(ge=0, le=10000)
    product_type: str = Field(min_length=3, max_length=80)
    audience: str = Field(min_length=3, max_length=200)
    deliverables: list[str] = Field(default_factory=list, max_length=40)
    preview_assets: list[str] = Field(default_factory=list, max_length=40)
    refund_policy: str = Field(default="", max_length=2000)
    support_text: str = Field(default="", max_length=2000)
    claims: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("deliverables", "preview_assets", "claims")
    @classmethod
    def clean_string_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ListingAuditResult(BaseModel):
    readiness_score: int = Field(ge=0, le=100)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    missing_assets: list[str] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    decision: Literal["launch", "revise", "quarantine"]
    ruleset_version: str
    platform_checklist: list[str] = Field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0

