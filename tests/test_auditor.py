import pytest
from pydantic import ValidationError

from passive_income_studio.auditor import audit_listing
from passive_income_studio.schemas import ListingAuditRequest, Platform


def valid_request(**updates: object) -> ListingAuditRequest:
    values = {
        "platform": Platform.fourthwall,
        "title": "AI Creator Workflow Bundle",
        "description": (
            "A three-product resource bundle for creators and independent service providers. "
            "It includes client intake templates, podcast repurposing workflows, and course "
            "production checklists. Files are digital downloads for personal or internal business use."
        ),
        "price": 39,
        "product_type": "resource bundle",
        "audience": "creators and independent service providers",
        "deliverables": ["Client intake kit", "Podcast workflow kit", "Course production kit"],
        "preview_assets": ["Square cover", "Interior preview"],
        "refund_policy": "Refund requests are reviewed when a file is defective or materially different.",
        "support_text": "Use the contact form. Replies are sent within two business days.",
        "claims": [],
    }
    values.update(updates)
    return ListingAuditRequest.model_validate(values)


def test_complete_listing_is_launch_ready() -> None:
    result = audit_listing(valid_request())
    assert result.decision == "launch"
    assert result.readiness_score >= 80
    assert not result.blocking_issues


def test_earnings_claim_is_quarantined() -> None:
    result = audit_listing(valid_request(claims=["Guaranteed to make $5000/month"]))
    assert result.decision == "quarantine"
    assert result.blocking_issues


def test_fake_scarcity_is_quarantined() -> None:
    result = audit_listing(valid_request(description=valid_request().description + " Only 3 left. Act now."))
    assert result.decision == "quarantine"


def test_missing_buyer_assets_requires_quarantine() -> None:
    result = audit_listing(valid_request(deliverables=[], preview_assets=[], refund_policy="", support_text=""))
    assert result.decision == "quarantine"
    assert "A concrete deliverables list" in result.missing_assets


def test_affiliate_copy_needs_disclosure() -> None:
    result = audit_listing(valid_request(description=valid_request().description + " This affiliate tool is included."))
    assert any("disclosure" in item.lower() for item in result.warnings)


def test_malformed_request_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ListingAuditRequest.model_validate({"platform": "Gumroad", "title": "x"})


@pytest.mark.parametrize("platform", list(Platform))
def test_every_platform_has_a_checklist(platform: Platform) -> None:
    result = audit_listing(valid_request(platform=platform))
    assert result.platform_checklist

