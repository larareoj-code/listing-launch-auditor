import pytest
from pydantic import ValidationError

from passive_income_studio.schemas import Deliverable, ExperimentCard, Platform, ProductType, RiskFlag


def test_deliverable_requires_provenance() -> None:
    with pytest.raises(ValidationError):
        Deliverable(
            name="Planner",
            kind="product_file",
            format="PDF",
            summary="A useful planner for weekly review.",
            provenance=[],
        )


def test_blocking_risk_requires_blocked_or_quarantined_status() -> None:
    with pytest.raises(ValidationError):
        ExperimentCard(
            hypothesis="A specific audience will buy a useful digital planner for organizing weekly sales work.",
            audience="solo consultants",
            buyer_job="organize weekly sales work",
            product_type=ProductType.template,
            deliverables=[
                Deliverable(
                    name="Planner",
                    kind="product_file",
                    format="PDF",
                    summary="A useful planner for weekly review.",
                    provenance=["Original generated structure"],
                )
            ],
            price=19,
            platform=Platform.gumroad,
            risk_flags=[
                RiskFlag(category="ip", severity="blocking", message="Blocked IP risk.", gate="IP Gate")
            ],
        )

