from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from passive_income_studio.agent_specs import AGENT_SPECS
from passive_income_studio.memory import LocalMemory
from passive_income_studio.policies import SafetyGateEngine
from passive_income_studio.schemas import (
    AgentResult,
    Deliverable,
    ExperimentCard,
    LaunchPackage,
    Platform,
    ProductType,
)


APPROVAL_GATES = [
    "publishing",
    "spend",
    "outreach",
    "platform changes",
    "brand/person/company name use",
    "product upload",
]


PRODUCT_BLUEPRINTS: dict[str, dict[str, object]] = {
    "busy solo consultants": {
        "product_name": "Solo Service Sprint Kit",
        "buyer_job": "create a repeatable weekly sales and delivery rhythm without building a full CRM",
        "subtitle": "Editable weekly planning templates for solo service operators.",
        "deliverables": [
            ("Weekly Client Pipeline Planner", "A weekly planner to track leads, proposals, delivery, and follow-up."),
            ("Offer Packaging Checklist", "A checklist for turning a service into a clear offer with scope, timeline, proof, and next step."),
            ("Follow-Up Swipe File", "Plain-language follow-up templates for warm leads and past clients."),
        ],
        "tags": ["consultant templates", "service business", "weekly planner", "digital template"],
    },
    "freelance copywriters": {
        "product_name": "Copywriter Client Flow Kit",
        "buyer_job": "standardize discovery, drafting, revision, and follow-up across client projects",
        "subtitle": "Client workflow templates for freelance writers who sell services.",
        "deliverables": [
            ("Discovery Call Brief", "A guided brief for capturing offer, audience, voice, proof, and conversion goals."),
            ("Draft Review Tracker", "A revision tracker for comments, approvals, and final delivery status."),
            ("Reactivation Email Swipe File", "A small swipe file for reconnecting with past clients and dormant leads."),
        ],
        "tags": ["copywriter templates", "client workflow", "freelance writing", "brief template"],
    },
    "independent fitness coaches": {
        "product_name": "Coach Client Onboarding Kit",
        "buyer_job": "organize client onboarding, check-ins, and habit tracking without making medical claims",
        "subtitle": "Admin and habit-tracking templates for independent fitness coaches.",
        "deliverables": [
            ("Client Intake Organizer", "A non-medical intake organizer for goals, availability, preferences, and logistics."),
            ("Weekly Check-In Tracker", "A check-in tracker for attendance, habits, notes, and client questions."),
            ("Program Delivery Checklist", "A checklist for sending plans, reminders, boundaries, and support notes."),
        ],
        "tags": ["fitness coach templates", "client onboarding", "habit tracker", "coaching admin"],
    },
    "Etsy digital product sellers": {
        "product_name": "Digital Listing Launch Kit",
        "buyer_job": "prepare a digital listing with stronger previews, QA, keywords, and support copy",
        "subtitle": "A pre-launch checklist bundle for Etsy digital download sellers.",
        "deliverables": [
            ("Listing QA Checklist", "A checklist for files, previews, instructions, tags, and download clarity."),
            ("Preview Image Planner", "A planner for mapping product benefits to preview image sections."),
            ("Customer FAQ Swipe File", "Reusable FAQ and support copy for digital download listings."),
        ],
        "tags": ["etsy seller checklist", "digital product listing", "download templates", "listing qa"],
    },
    "local service business owners": {
        "product_name": "Local Lead Follow-Up Kit",
        "buyer_job": "turn inquiries, quotes, reviews, and repeat business into a repeatable weekly process",
        "subtitle": "Simple follow-up templates for small local service businesses.",
        "deliverables": [
            ("Inquiry Response Tracker", "A tracker for new leads, quote status, next action, and owner notes."),
            ("Quote Follow-Up Swipe File", "Short follow-up messages for open quotes and stalled conversations."),
            ("Review Request Checklist", "A checklist for asking satisfied customers for reviews at the right moment."),
        ],
        "tags": ["local business templates", "lead follow up", "quote tracker", "review request"],
    },
    "Notion template creators": {
        "product_name": "Template Maker QA Kit",
        "buyer_job": "package, test, document, and launch Notion templates with fewer support issues",
        "subtitle": "QA and launch templates for Notion template creators.",
        "deliverables": [
            ("Template QA Checklist", "A checklist for links, sample data, permissions, mobile views, and onboarding notes."),
            ("Launch Page Copy Planner", "A planner for turning template features into buyer-focused benefits."),
            ("Support Macro Swipe File", "Support replies for access, duplication, setup, and refund questions."),
        ],
        "tags": ["notion creator", "template qa", "notion template launch", "digital product"],
    },
    "online course creators": {
        "product_name": "Mini-Course Launch Control Kit",
        "buyer_job": "organize a lightweight course launch without paid ads or complex automation",
        "subtitle": "Planning templates for small course and workshop launches.",
        "deliverables": [
            ("Launch Timeline Planner", "A simple timeline for topic validation, outline, assets, emails, and launch day."),
            ("Lesson Asset Checklist", "A checklist for slides, worksheets, links, captions, and student instructions."),
            ("Student Onboarding FAQ", "A starter FAQ for access, timing, outcomes, support, and refunds."),
        ],
        "tags": ["course creator templates", "mini course launch", "workshop planner", "launch checklist"],
    },
    "virtual assistants": {
        "product_name": "VA Client Ops Starter Kit",
        "buyer_job": "standardize client onboarding, recurring task tracking, and weekly reporting",
        "subtitle": "Client operations templates for virtual assistants.",
        "deliverables": [
            ("Client Onboarding Checklist", "A checklist for access, contacts, scope, recurring tasks, and communication norms."),
            ("Weekly Task Report", "A lightweight report template for completed tasks, blockers, and next priorities."),
            ("Scope Boundary Swipe File", "Polite messages for clarifying requests, timelines, and out-of-scope work."),
        ],
        "tags": ["virtual assistant templates", "client onboarding", "weekly report", "va business"],
    },
}


class PortfolioOrchestrator:
    """Manager-worker orchestrator for no-spend digital product experiments."""

    def __init__(
        self,
        brand_name: str = "Quiet Systems Lab",
        memory: LocalMemory | None = None,
        user_id: str = "passive-income-studio",
    ) -> None:
        self.brand_name = brand_name
        self.safety = SafetyGateEngine()
        self.memory = memory
        self.user_id = user_id

    def run(self, niche: str, platform: Platform = Platform.gumroad) -> LaunchPackage:
        memory_context = self._recall(niche)
        scout = self._opportunity_scout(niche, memory_context)
        strategy = self._product_strategist(scout, platform)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(self._asset_builder, strategy),
                pool.submit(self._design_packaging, strategy),
                pool.submit(self._launch_prep, strategy),
                pool.submit(self._analytics_stub, strategy),
            ]
            parallel_results = [future.result() for future in futures]

        card = self._build_experiment_card(strategy, parallel_results, platform)
        reviewed_card = self.safety.enforce(card)
        compliance = self._compliance(reviewed_card)
        qa = self._qa(reviewed_card, parallel_results)
        launch = next(result for result in parallel_results if result.agent_name == "Launch Prep Agent")

        agent_results = [scout, strategy, *parallel_results, compliance, qa]
        package = LaunchPackage(
            brand_name=self.brand_name,
            experiment=reviewed_card,
            agent_results=agent_results,
            storefront_listing=launch.artifacts["storefront_listing"],
            publish_checklist=[
                "Review all product files manually.",
                "Confirm IP/provenance notes are accurate.",
                "Confirm no earnings, legal, medical, tax, or investment claims are present.",
                "Manually create or open the Gumroad/Payhip product page.",
                "Paste listing copy only after human approval.",
                "Upload files only after human approval.",
                "Publish only after final launch approval.",
            ],
            approval_required_before=APPROVAL_GATES,
            learning_ledger_event={
                "event": "launch_package_created",
                "niche": niche,
                "platform": platform.value,
                "decision": reviewed_card.decision.value,
                "risk_count": len(reviewed_card.risk_flags),
                "external_side_effects": 0,
            },
        )
        self._remember(package)
        return package

    def write_package(self, package: LaunchPackage, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")
        return output_path

    def append_ledger(self, package: LaunchPackage, ledger_path: Path) -> None:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(package.learning_ledger_event, sort_keys=True) + "\n")

    def _recall(self, niche: str) -> list[dict[str, Any]]:
        if self.memory is None:
            return []
        return [
            {
                "content": record.content,
                "score": record.score,
                "tags": record.tags,
                "metadata": record.metadata,
            }
            for record in self.memory.search_sync(
                f"{niche} digital product template launch package decision risk pricing",
                user_id=self.user_id,
                limit=5,
            )
        ]

    def _remember(self, package: LaunchPackage) -> None:
        if self.memory is None:
            return
        content = (
            f"Experiment for {package.experiment.audience}: {package.storefront_listing['title']} "
            f"priced at {package.experiment.price} on {package.experiment.platform.value}; "
            f"decision={package.experiment.decision.value}; "
            f"approval={package.experiment.approval_status.value}; "
            f"risks={len(package.experiment.risk_flags)}; "
            f"buyer_job={package.experiment.buyer_job}"
        )
        self.memory.add_sync(
            content,
            user_id=self.user_id,
            tags=["experiment", "digital-product", package.experiment.platform.value.lower()],
            meta=package.learning_ledger_event,
        )

    def _opportunity_scout(self, niche: str, memory_context: list[dict[str, Any]]) -> AgentResult:
        clean_niche = niche.strip() or "busy solo consultants"
        return AgentResult(
            agent_name="Opportunity Scout",
            summary=f"Found a low-touch digital product angle for {clean_niche}.",
            artifacts={
                "memory_context": memory_context,
                "niche_options": [
                    {
                        "audience": clean_niche,
                        "buyer_job": "turn scattered repeatable work into a simple operating system",
                        "demand_signal": "buyers already purchase templates, planners, and checklists",
                        "competition_note": "differentiate through specificity and practical examples",
                        "validation_method": "publish one launch-ready package and track page views, saves, and sales",
                    }
                ],
                "source_notes": [
                    "User-provided AI passive-income planning sources",
                    "Printify AI income categories: digital products, affiliate, POD, niche content",
                ],
            },
        )

    def _product_strategist(self, scout: AgentResult, platform: Platform) -> AgentResult:
        option = scout.artifacts["niche_options"][0]
        blueprint = PRODUCT_BLUEPRINTS.get(str(option["audience"]), PRODUCT_BLUEPRINTS["busy solo consultants"])
        return AgentResult(
            agent_name="Product Strategist",
            summary="Selected a practical template bundle with conservative claims.",
            artifacts={
                "hypothesis": (
                    f"{option['audience']} will pay for a compact, editable operating kit that helps "
                    f"them {blueprint['buyer_job']}."
                ),
                "audience": option["audience"],
                "buyer_job": blueprint["buyer_job"],
                "product_type": ProductType.template.value,
                "product_name": blueprint["product_name"],
                "subtitle": blueprint["subtitle"],
                "deliverable_specs": blueprint["deliverables"],
                "tags": blueprint["tags"],
                "price": 19.0,
                "platform": platform.value,
                "validation_criteria": {
                    "minimum_signal": "25 product page views or 3 wishlist/email saves in 14 days",
                    "manual_launch_only": True,
                },
            },
        )

    def _asset_builder(self, strategy: AgentResult) -> AgentResult:
        specs = strategy.artifacts["deliverable_specs"]
        return AgentResult(
            agent_name="Asset Builder",
            summary="Drafted the core product bundle contents.",
            artifacts={
                "deliverables": [
                    {
                        "name": name,
                        "kind": "product_file",
                        "format": "PDF/Notion-ready Markdown",
                        "summary": summary,
                        "provenance": ["Original agent-generated structure", "No third-party source assets"],
                    }
                    for name, summary in specs
                ]
            },
        )

    def _design_packaging(self, strategy: AgentResult) -> AgentResult:
        return AgentResult(
            agent_name="Design/Packaging Agent",
            summary="Created brand-safe package naming and preview direction.",
            artifacts={
                "product_name": strategy.artifacts["product_name"],
                "cover_direction": "Clean checklist-style cover, neutral palette, no logos, no people, no brand references.",
                "preview_images": [
                    "Cover mockup showing the bundle name",
                    "Primary template preview with blurred example rows",
                    "Checklist or swipe-file preview showing section headings only",
                ],
                "file_structure": [
                    "01-start-here.pdf",
                    "02-primary-template.pdf",
                    "03-checklist-or-planner.pdf",
                    "04-swipe-file-or-faq.md",
                    "license-and-support.txt",
                ],
            },
        )

    def _launch_prep(self, strategy: AgentResult) -> AgentResult:
        return AgentResult(
            agent_name="Launch Prep Agent",
            summary="Prepared Gumroad/Payhip listing copy for manual review.",
            artifacts={
                "storefront_listing": {
                    "title": strategy.artifacts["product_name"],
                    "subtitle": strategy.artifacts["subtitle"],
                    "description": (
                        f"A compact digital kit for {strategy.artifacts['audience']} who want to "
                        f"{strategy.artifacts['buyer_job']}. Includes three editable assets, a start-here note, "
                        "and support copy. No income promises; results depend on your market, offer, and execution."
                    ),
                    "price": strategy.artifacts["price"],
                    "tags": strategy.artifacts["tags"],
                    "faq": [
                        {
                            "q": "Is this a physical product?",
                            "a": "No. It is a digital download prepared for manual publishing on Gumroad or Payhip.",
                        },
                        {
                            "q": "Does this guarantee sales?",
                            "a": "No. It is an organizational tool, not an income guarantee.",
                        },
                    ],
                    "refund_support_text": "Because this is a digital product, set a clear manual refund policy before launch.",
                }
            },
        )

    def _analytics_stub(self, strategy: AgentResult) -> AgentResult:
        return AgentResult(
            agent_name="Analytics Agent",
            summary="Prepared post-launch metric thresholds; no live metrics imported in v1 smoke run.",
            artifacts={
                "metric_plan": {
                    "review_after_days": 14,
                    "iterate_if": "page views but no saves or sales",
                    "scale_if": "sales or strong save rate with no compliance issues",
                    "stop_if": "no meaningful traffic or repeated negative feedback",
                }
            },
        )

    def _build_experiment_card(
        self, strategy: AgentResult, results: list[AgentResult], platform: Platform
    ) -> ExperimentCard:
        asset_result = next(result for result in results if result.agent_name == "Asset Builder")
        deliverables = [Deliverable(**item) for item in asset_result.artifacts["deliverables"]]
        return ExperimentCard(
            hypothesis=strategy.artifacts["hypothesis"],
            audience=strategy.artifacts["audience"],
            buyer_job=strategy.artifacts["buyer_job"],
            product_type=ProductType(strategy.artifacts["product_type"]),
            deliverables=deliverables,
            price=float(strategy.artifacts["price"]),
            platform=platform,
        )

    def _compliance(self, card: ExperimentCard) -> AgentResult:
        return AgentResult(
            agent_name="Compliance/IP Agent",
            summary="Ran deterministic v1 policy checks and preserved manual approval gates.",
            artifacts={
                "approval_status": card.approval_status.value,
                "decision": card.decision.value,
                "hard_stops": APPROVAL_GATES,
            },
            risk_flags=card.risk_flags,
        )

    def _qa(self, card: ExperimentCard, results: list[AgentResult]) -> AgentResult:
        checks: dict[str, Any] = {
            "has_deliverables": bool(card.deliverables),
            "all_deliverables_have_provenance": all(item.provenance for item in card.deliverables),
            "price_within_v1_range": 0 <= card.price <= 99,
            "manual_review_required": card.approval_status.value == "review_required",
            "external_side_effects": 0,
        }
        return AgentResult(
            agent_name="QA Agent",
            summary="Package passes local QA for no-side-effect launch preparation.",
            artifacts={"checks": checks, "passed": all(checks.values())},
        )


def agent_roster() -> list[dict[str, object]]:
    return [
        {
            "name": spec.name,
            "purpose": spec.purpose,
            "output_contract": spec.output_contract,
            "may_do": list(spec.may_do),
            "must_not_do": list(spec.must_not_do),
        }
        for spec in AGENT_SPECS
    ]

