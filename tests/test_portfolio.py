from pathlib import Path

from passive_income_studio.memory import LocalMemory
from passive_income_studio.orchestrator import PortfolioOrchestrator
from passive_income_studio.portfolio import NicheBrief, generate_launch_queue


def test_generate_launch_queue_writes_manifest_and_packages(tmp_path: Path) -> None:
    orchestrator = PortfolioOrchestrator(memory=LocalMemory(tmp_path / "memory.sqlite"))
    manifest = generate_launch_queue(
        orchestrator,
        tmp_path / "queue",
        briefs=(
            NicheBrief("busy solo consultants", score=90),
            NicheBrief("freelance copywriters", score=80),
        ),
    )

    assert manifest["summary"]["packages"] == 2
    assert manifest["summary"]["external_side_effects"] == 0
    assert (tmp_path / "queue" / "launch-manifest.json").exists()
    assert len(list((tmp_path / "queue").glob("*.json"))) == 3

