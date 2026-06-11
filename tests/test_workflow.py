from passive_income_studio.orchestrator import PortfolioOrchestrator


def test_workflow_creates_review_ready_launch_package() -> None:
    package = PortfolioOrchestrator().run("busy solo consultants")

    assert package.experiment.approval_status.value == "review_required"
    assert package.experiment.decision.value == "launch_review"
    assert package.learning_ledger_event["external_side_effects"] == 0
    assert "publishing" in package.approval_required_before
    assert package.storefront_listing["title"]
    assert all(item.provenance for item in package.experiment.deliverables)


def test_agent_roster_includes_required_specialists() -> None:
    names = {result.agent_name for result in PortfolioOrchestrator().run("busy solo consultants").agent_results}
    assert "Opportunity Scout" in names
    assert "Compliance/IP Agent" in names
    assert "Launch Prep Agent" in names

