from pathlib import Path

from passive_income_studio.exporter import export_product_bundle
from passive_income_studio.orchestrator import PortfolioOrchestrator


def test_export_product_bundle_creates_zip(tmp_path: Path) -> None:
    package = PortfolioOrchestrator().run("busy solo consultants")
    package_path = tmp_path / "package.json"
    package_path.write_text(package.model_dump_json(), encoding="utf-8")

    manifest = export_product_bundle(package_path, tmp_path / "export")

    assert Path(manifest["zip_path"]).exists()
    assert any(path.endswith("gumroad-listing-copy.md") for path in manifest["files"])
    assert manifest["external_side_effects"] == 0

