from pathlib import Path

from passive_income_studio.idea_sources import load_income_generator, load_make_money_with_ai


def test_load_make_money_with_ai_digest(tmp_path: Path) -> None:
    csv_path = tmp_path / "repos.csv"
    csv_path.write_text(
        "id,owner,name,stars,url,business_model\n"
        "1,o,n8n,10,https://example.com,AI workflow automation templates and integrations\n"
        "2,o,img,5,https://example.com,AI image products and merchandise\n",
        encoding="utf-8",
    )

    digest = load_make_money_with_ai(csv_path, limit=2)

    assert digest["source"] == "garylab/MakeMoneyWithAI"
    assert digest["rows_total"] == 2
    assert digest["category_counts"]["automation"] == 1
    assert digest["category_counts"]["image_video_audio"] == 1


def test_load_income_generator_digest(tmp_path: Path) -> None:
    apps_path = tmp_path / "apps.json"
    apps_path.write_text(
        """
        [
          {
            "name": "TESTGAIN",
            "properties": ["TEST_EMAIL", "TEST_PASSWORD"],
            "is_enabled": true,
            "service_enabled": true,
            "proxy_uuid": {"name_type": "UUID"}
          }
        ]
        """,
        encoding="utf-8",
    )

    digest = load_income_generator(apps_path)

    assert digest["source"] == "XternA/income-generator"
    assert digest["apps_total"] == 1
    assert digest["credentialed_apps"] == 1
    assert digest["proxy_or_device_apps"] == 1
    assert "high-risk" in digest["recommendation"]

