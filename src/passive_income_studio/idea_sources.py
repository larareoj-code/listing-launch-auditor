from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


CATEGORY_KEYWORDS = {
    "automation": ["automation", "workflow", "agent", "browser", "integrations"],
    "digital_products": ["template", "prompt", "course", "training", "content"],
    "image_video_audio": ["image", "video", "voice", "audio", "tts", "merchandise"],
    "knowledge_rag": ["rag", "search", "knowledge", "document", "retrieval"],
    "developer_tools": ["code", "developer", "testing", "ci/cd", "prototype"],
    "analytics": ["analytics", "dashboard", "data", "report", "monitoring"],
    "local_inference": ["local", "self-hosted", "inference", "ollama", "private"],
}


def load_make_money_with_ai(csv_path: Path, limit: int = 40) -> dict[str, Any]:
    rows = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    top_rows = sorted(rows, key=lambda row: int(row.get("stars") or 0), reverse=True)[:limit]
    category_counts: Counter[str] = Counter()
    idea_lines: list[str] = []

    for row in top_rows:
        business_model = strip_markdown(row.get("business_model", ""))
        categories = categorize(business_model)
        category_counts.update(categories)
        idea_lines.append(
            f"{row['owner']}/{row['name']} ({row['stars']} stars): "
            f"{', '.join(categories) or 'general'} - {business_model}"
        )

    return {
        "source": "garylab/MakeMoneyWithAI",
        "rows_total": len(rows),
        "rows_ingested": len(top_rows),
        "category_counts": dict(category_counts.most_common()),
        "top_ideas": idea_lines,
    }


def load_income_generator(apps_path: Path) -> dict[str, Any]:
    apps = json.loads(apps_path.read_text(encoding="utf-8"))
    payout_counts: Counter[str] = Counter()
    risk_notes: list[str] = []
    app_summaries: list[str] = []

    for app in apps:
        properties = app.get("properties") or []
        description = " ".join(
            value
            for value in [app.get("description"), app.get("description_ext"), app.get("registration")]
            if value
        )
        if "PayPal" in description or "paypal" in description:
            payout_counts["paypal"] += 1
        if "Crypto" in description or "crypto" in description:
            payout_counts["crypto"] += 1
        if properties:
            risk_notes.append(f"{app['name']} requires credentials or account identifiers: {', '.join(properties)}")
        if app.get("proxy_port") or app.get("proxy_uuid"):
            risk_notes.append(f"{app['name']} exposes proxy/device registration behavior.")
        app_summaries.append(
            f"{app['name']}: properties={len(properties)}, install_limit={app.get('install_limit', 'default')}, "
            f"proxy={bool(app.get('proxy_port') or app.get('proxy_uuid'))}"
        )

    return {
        "source": "XternA/income-generator",
        "apps_total": len(apps),
        "enabled_apps": sum(1 for app in apps if app.get("is_enabled")),
        "service_apps": sum(1 for app in apps if app.get("service_enabled")),
        "credentialed_apps": sum(1 for app in apps if app.get("properties")),
        "proxy_or_device_apps": sum(1 for app in apps if app.get("proxy_port") or app.get("proxy_uuid")),
        "payout_counts": dict(payout_counts),
        "app_summaries": app_summaries,
        "risk_notes": risk_notes[:20],
        "recommendation": (
            "Treat bandwidth-sharing/proxy income as high-risk and out of scope for autonomous v1. "
            "Require legal, ISP, privacy, device-security, tax, account, and platform review before use."
        ),
    }


def categorize(text: str) -> list[str]:
    lowered = text.lower()
    return [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def strip_markdown(text: str) -> str:
    text = re.sub(r"[*_`#>\[\]]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

