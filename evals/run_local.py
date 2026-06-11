from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from passive_income_studio.orchestrator import PortfolioOrchestrator
from passive_income_studio.policies import SafetyGateEngine


def main() -> int:
    cases_path = ROOT / "evals" / "cases.jsonl"
    results_dir = ROOT / "evals" / "results"
    results_dir.mkdir(exist_ok=True)

    gate = SafetyGateEngine()
    orchestrator = PortfolioOrchestrator()
    results = []
    failures = []

    for line in cases_path.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if "niche" in case:
            package = orchestrator.run(case["niche"])
            passed = (
                package.experiment.decision.value == case["expected_decision"]
                and package.learning_ledger_event["external_side_effects"] == case["expected_external_side_effects"]
            )
            result = {"id": case["id"], "passed": passed}
        else:
            flags = gate.evaluate_text(case["text"])
            passed = any(flag.category == case["expected_blocking_category"] for flag in flags)
            result = {"id": case["id"], "passed": passed, "flags": [flag.model_dump() for flag in flags]}
        results.append(result)
        if not passed:
            failures.append(case["id"])

    (results_dir / "latest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if failures:
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        return 1
    print(json.dumps({"passed": True, "cases": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

