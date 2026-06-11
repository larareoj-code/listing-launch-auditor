from pathlib import Path

from passive_income_studio.memory import LocalMemory
from passive_income_studio.orchestrator import PortfolioOrchestrator


def test_local_memory_add_search_history(tmp_path: Path) -> None:
    memory = LocalMemory(tmp_path / "memory.sqlite")
    memory.add_sync(
        "Experiment for solo consultants priced at 19 on Gumroad",
        user_id="u1",
        tags=["experiment"],
        meta={"decision": "launch_review"},
    )

    results = memory.search_sync("solo consultants Gumroad", user_id="u1")
    assert results
    assert results[0].metadata["decision"] == "launch_review"
    assert memory.history(user_id="u1", limit=1)[0]["content"].startswith("Experiment")


def test_orchestrator_recalls_prior_memory(tmp_path: Path) -> None:
    memory = LocalMemory(tmp_path / "memory.sqlite")
    orchestrator = PortfolioOrchestrator(memory=memory)
    orchestrator.run("busy solo consultants")
    second = orchestrator.run("busy solo consultants")

    scout = next(result for result in second.agent_results if result.agent_name == "Opportunity Scout")
    assert scout.artifacts["memory_context"]

