from __future__ import annotations

import re
from dataclasses import dataclass

from passive_income_studio.policies import SafetyGateEngine
from passive_income_studio.schemas import ListingAuditRequest, ListingAuditResult, Platform


RULESET_VERSION = "2026.06.1"


@dataclass(frozen=True)
class PlatformProfile:
    checklist: tuple[str, ...]
    recommended_previews: int


PLATFORM_PROFILES = {
    Platform.gumroad: PlatformProfile(
        ("Confirm the product URL slug.", "Attach the final downloadable files.", "Preview the checkout and receipt."), 2
    ),
    Platform.payhip: PlatformProfile(
        ("Confirm digital-product tax settings.", "Attach the final downloadable files.", "Preview the sales page and checkout."), 2
    ),
    Platform.kofi: PlatformProfile(
        ("Disable pay-what-you-want unless intentional.", "Confirm the original-content declaration.", "Test the buyer download."), 1
    ),
    Platform.fourthwall: PlatformProfile(
        ("Set the listing to Public.", "Confirm the storefront itself is Live.", "Test the cart and digital delivery."), 1
    ),
    Platform.buy_me_a_coffee: PlatformProfile(
        ("Confirm payout and identity review status.", "Verify the product appears in the public Shop tab.", "Test the public product page."), 1
    ),
}


URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
SCARCITY_PATTERN = re.compile(r"\b(?:only\s+\d+\s+left|ends?\s+today|last\s+chance|act\s+now)\b", re.IGNORECASE)
TRADEMARK_HINTS = ("official", "fan art", "inspired by", "compatible with")


def _add_unique(target: list[str], message: str) -> None:
    if message not in target:
        target.append(message)


def audit_listing(request: ListingAuditRequest) -> ListingAuditResult:
    blocking: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    missing_assets: list[str] = []
    compliance: list[str] = []
    deductions = 0
    checks_total = 12
    failed_checks = 0

    corpus = " ".join([request.title, request.description, request.refund_policy, request.support_text, *request.claims])
    safety_flags = SafetyGateEngine().evaluate_text(corpus)
    for flag in safety_flags:
        _add_unique(compliance, flag.message)
        if flag.severity == "blocking":
            _add_unique(blocking, flag.message)
            deductions += 35
            failed_checks += 1
        else:
            _add_unique(warnings, flag.message)
            deductions += 8
            failed_checks += 1

    if SCARCITY_PATTERN.search(corpus):
        _add_unique(blocking, "Potential fake or unverifiable scarcity language detected.")
        _add_unique(compliance, "Scarcity must be factual, time-bound, and independently verifiable.")
        deductions += 30
        failed_checks += 1

    lowered = corpus.lower()
    if any(term in lowered for term in TRADEMARK_HINTS):
        _add_unique(warnings, "Brand-compatibility or inspiration language needs trademark and affiliation review.")
        deductions += 8
        failed_checks += 1

    if not request.deliverables:
        _add_unique(blocking, "No buyer deliverables are listed.")
        _add_unique(missing_assets, "A concrete deliverables list")
        deductions += 25
        failed_checks += 1
    elif len(request.deliverables) < 2:
        _add_unique(warnings, "Clarify the file format and quantity for each deliverable.")
        deductions += 5

    profile = PLATFORM_PROFILES[request.platform]
    if len(request.preview_assets) < profile.recommended_previews:
        _add_unique(missing_assets, f"At least {profile.recommended_previews} clear product preview asset(s)")
        _add_unique(warnings, "The listing needs more buyer-facing previews.")
        deductions += 12
        failed_checks += 1

    if not request.refund_policy.strip():
        _add_unique(missing_assets, "Refund or cancellation policy")
        _add_unique(warnings, "Add a clear refund policy before launch.")
        deductions += 10
        failed_checks += 1

    if not request.support_text.strip():
        _add_unique(missing_assets, "Support contact or response-time note")
        _add_unique(warnings, "Tell buyers how to request product support.")
        deductions += 8
        failed_checks += 1

    if len(request.description.split()) < 35:
        _add_unique(warnings, "The description is brief; add the buyer outcome, contents, format, and limits.")
        deductions += 8
        failed_checks += 1

    if request.price == 0:
        _add_unique(recommendations, "State that the product is free and explain what the buyer receives.")
    elif request.price >= 25 and len(request.deliverables) < 3:
        _add_unique(warnings, "The price may need stronger value proof or a more detailed bundle breakdown.")
        deductions += 6

    urls = URL_PATTERN.findall(corpus)
    if any(url.endswith((".", ",", ")")) for url in urls):
        _add_unique(warnings, "One or more pasted links may include trailing punctuation; test every link.")
        deductions += 4

    if request.audience.lower() not in request.description.lower():
        _add_unique(recommendations, "Name the intended buyer directly in the opening description.")
    if request.product_type.lower() not in lowered:
        _add_unique(recommendations, "State the product format explicitly so buyers know what they are purchasing.")
    if not request.claims:
        _add_unique(recommendations, "List any measurable claims separately so they can be verified before publishing.")

    score = max(0, min(100, 100 - deductions))
    if blocking:
        decision = "quarantine"
    elif score >= 80 and not missing_assets:
        decision = "launch"
    else:
        decision = "revise"

    if decision == "launch":
        _add_unique(recommendations, "Run one final checkout and download test before publishing.")
    elif decision == "revise":
        _add_unique(recommendations, "Resolve missing assets and warnings, then run the audit again.")
    else:
        _add_unique(recommendations, "Remove or substantiate blocking language before any public launch.")

    return ListingAuditResult(
        readiness_score=score,
        blocking_issues=blocking,
        warnings=warnings,
        recommendations=recommendations,
        missing_assets=missing_assets,
        compliance_flags=compliance,
        decision=decision,
        ruleset_version=RULESET_VERSION,
        platform_checklist=list(profile.checklist),
        checks_passed=max(0, checks_total - min(checks_total, failed_checks)),
        checks_total=checks_total,
    )

