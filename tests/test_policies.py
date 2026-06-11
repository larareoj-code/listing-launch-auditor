from passive_income_studio.policies import SafetyGateEngine


def test_blocks_unsupported_earnings_claim() -> None:
    flags = SafetyGateEngine().evaluate_text("Make $5000/month guaranteed with this passive kit.")
    assert any(flag.category == "claims" and flag.severity == "blocking" for flag in flags)


def test_blocks_ip_risk_terms() -> None:
    flags = SafetyGateEngine().evaluate_text("Create a Disney-style planner.")
    assert any(flag.category == "ip" and flag.severity == "blocking" for flag in flags)


def test_flags_affiliate_disclosure() -> None:
    flags = SafetyGateEngine().evaluate_text("This affiliate offer is useful.")
    assert any(flag.category == "disclosure" for flag in flags)

