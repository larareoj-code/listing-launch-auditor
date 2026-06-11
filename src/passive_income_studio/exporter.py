from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from passive_income_studio.schemas import LaunchPackage


def export_product_bundle(package_path: Path, output_dir: Path) -> dict[str, Any]:
    package = LaunchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
    product_slug = slugify(str(package.storefront_listing["title"]))
    product_dir = output_dir / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    files.append(write_start_here(product_dir, package))
    for index, deliverable in enumerate(package.experiment.deliverables, start=2):
        files.append(write_deliverable(product_dir, index, deliverable.name, deliverable.summary))
    files.append(write_license(product_dir, package))
    files.append(write_gumroad_listing(product_dir, package))

    zip_path = output_dir / f"{product_slug}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=f"{product_slug}/{path.name}")

    manifest = {
        "title": package.storefront_listing["title"],
        "price": package.experiment.price,
        "platform": package.experiment.platform.value,
        "product_dir": str(product_dir),
        "zip_path": str(zip_path),
        "files": [str(path) for path in files],
        "external_side_effects": 0,
        "approval_required_before_publish": package.approval_required_before,
    }
    (product_dir / "bundle-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def write_start_here(product_dir: Path, package: LaunchPackage) -> Path:
    path = product_dir / "01-start-here.md"
    listing = package.storefront_listing
    text = f"""# {listing["title"]}

{listing["subtitle"]}

## What This Is

{listing["description"]}

## How To Use This Kit

1. Read each template once before editing.
2. Duplicate the templates into your preferred workspace.
3. Replace example language with your own business details.
4. Review the checklist before using any client-facing message.
5. Keep a copy of the original files for future launches.

## Important Note

This kit is an organizational tool. It does not promise income, clients, health results, legal outcomes, or financial results.
"""
    path.write_text(text, encoding="utf-8")
    return path


def write_deliverable(product_dir: Path, index: int, name: str, summary: str) -> Path:
    path = product_dir / f"{index:02d}-{slugify(name)}.md"
    text = f"""# {name}

{summary}

## Template

### Goal

Use this page to make the next action obvious and repeatable.

### Inputs

- Audience or client:
- Current status:
- Desired outcome:
- Next deadline:
- Owner:

### Working Section

| Item | Detail | Status | Next Action |
| --- | --- | --- | --- |
| Example | Replace this with your real workflow item. | Draft | Decide the next step. |
|  |  |  |  |
|  |  |  |  |

### Review Checklist

- The next action is specific.
- Any client-facing wording has been reviewed by a human.
- No unsupported earnings, health, legal, tax, or financial claim is included.
- No third-party brand, celebrity, character, or private material is used.

### Notes

- 
- 
- 
"""
    path.write_text(text, encoding="utf-8")
    return path


def write_license(product_dir: Path, package: LaunchPackage) -> Path:
    path = product_dir / "license-and-support.txt"
    text = f"""License and Support

Product: {package.storefront_listing["title"]}

Personal-use license:
- You may copy and edit these files for your own business or personal workflow.
- You may not resell, redistribute, sublicense, or upload these files as your own product.

Support:
- Add your support email before publishing this product.
- Add your refund policy before publishing this product.

AI/provenance note:
- This product was generated from original structured templates and requires human review before sale.
- No third-party source assets are intentionally included.
"""
    path.write_text(text, encoding="utf-8")
    return path


def write_gumroad_listing(product_dir: Path, package: LaunchPackage) -> Path:
    path = product_dir / "gumroad-listing-copy.md"
    listing = package.storefront_listing
    faq = "\n".join(f"- **{item['q']}** {item['a']}" for item in listing["faq"])
    tags = ", ".join(listing["tags"])
    text = f"""# Gumroad Listing Copy

## Title
{listing["title"]}

## Subtitle
{listing["subtitle"]}

## Price
${listing["price"]}

## Description
{listing["description"]}

## Tags
{tags}

## FAQ
{faq}

## Refund/Support Note
{listing["refund_support_text"]}

## Publish Gate
Do not publish until the final product files, support email, refund policy, and storefront preview have been reviewed.
"""
    path.write_text(text, encoding="utf-8")
    return path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"

