from __future__ import annotations

import pytest

from passive_income_studio.billing import BillingConfigurationError, create_checkout_session, resolve_public_origin


def test_checkout_fails_closed_without_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_PRICE_MONTHLY", raising=False)

    with pytest.raises(BillingConfigurationError, match="not configured"):
        create_checkout_session("monthly", "https://example.test")


def test_public_origin_allows_local_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_URL", raising=False)
    assert resolve_public_origin("http://127.0.0.1:8790") == "http://127.0.0.1:8790"


def test_public_origin_requires_config_for_remote_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_URL", raising=False)
    with pytest.raises(BillingConfigurationError, match="APP_URL"):
        resolve_public_origin("https://attacker.example")


def test_public_origin_uses_configured_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_URL", "https://auditor.example/")
    assert resolve_public_origin("https://attacker.example") == "https://auditor.example"

