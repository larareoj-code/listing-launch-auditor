from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from passive_income_studio.orchestrator import PortfolioOrchestrator
from passive_income_studio.schemas import LaunchPackage, Platform


@dataclass(frozen=True)
class NicheBrief:
    niche: str
    platform: Platform = Platform.gumroad
    score: int = 50
    rationale: str = "General digital product opportunity."


DEFAULT_NICHES: tuple[NicheBrief, ...] = (
    NicheBrief(
        niche="busy solo consultants",
        score=86,
        rationale="Clear buyer job, low production cost, strong fit for templates.",
    ),
    NicheBrief(
        niche="freelance copywriters",
        score=82,
        rationale="Repeatable client workflow; likely to buy swipe files and planning templates.",
    ),
    NicheBrief(
        niche="independent fitness coaches",
        score=78,
        rationale="Needs client onboarding and habit tracking, while avoiding health claims.",
    ),
    NicheBrief(
        niche="Etsy digital product sellers",
        score=76,
        rationale="Already buys templates and checklists; good meta-market for launch systems.",
    ),
    NicheBrief(
        niche="local service business owners",
        score=74,
        rationale="Needs follow-up, quote, and review-request processes without full software.",
    ),
    NicheBrief(
        niche="Notion template creators",
        score=72,
        rationale="Template-native audience with clear packaging and QA needs.",
    ),
    NicheBrief(
        niche="online course creators",
        score=70,
        rationale="Needs launch planning, content reuse, and student onboarding assets.",
    ),
    NicheBrief(
        niche="virtual assistants",
        score=69,
        rationale="Repeatable service delivery and onboarding workflows fit checklists well.",
    ),
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "launch-package"


def generate_launch_queue(
    orchestrator: PortfolioOrchestrator,
    output_dir: Path,
    briefs: tuple[NicheBrief, ...] = DEFAULT_NICHES,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    packages: list[LaunchPackage] = []
    manifest_items: list[dict[str, object]] = []

    for rank, brief in enumerate(sorted(briefs, key=lambda item: item.score, reverse=True), start=1):
        package = orchestrator.run(brief.niche, platform=brief.platform)
        package_path = output_dir / f"{rank:02d}-{slugify(brief.niche)}.json"
        package_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")
        packages.append(package)
        manifest_items.append(
            {
                "rank": rank,
                "niche": brief.niche,
                "score": brief.score,
                "rationale": brief.rationale,
                "package_file": package_path.name,
                "title": package.storefront_listing["title"],
                "price": package.experiment.price,
                "platform": package.experiment.platform.value,
                "decision": package.experiment.decision.value,
                "approval_status": package.experiment.approval_status.value,
                "risk_count": len(package.experiment.risk_flags),
                "external_side_effects": 0,
            }
        )

    manifest = {
        "summary": {
            "packages": len(packages),
            "ready_for_manual_review": sum(
                1 for package in packages if package.experiment.decision.value == "launch_review"
            ),
            "external_side_effects": 0,
            "publish_requires_manual_approval": True,
        },
        "queue": manifest_items,
    }
    (output_dir / "launch-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

