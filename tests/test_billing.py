from __future__ import annotations

import pytest
from types import SimpleNamespace

from passive_income_studio.billing import (
    BillingConfigurationError,
    create_checkout_session,
    resolve_public_origin,
    verify_checkout_entitlement,
)


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


def test_invalid_entitlement_session_is_rejected() -> None:
    assert verify_checkout_entitlement("not-a-session") == {"active": False, "reason": "invalid_session"}


def test_active_subscription_unlocks_pro(monkeypatch: pytest.MonkeyPatch) -> None:
    class CheckoutSession:
        @staticmethod
        def retrieve(session_id: str) -> dict[str, object]:
            assert session_id == "cs_test_verified"
            return {
                "mode": "subscription",
                "status": "complete",
                "subscription": "sub_verified",
                "metadata": {"plan": "yearly"},
            }

    class Subscription:
        @staticmethod
        def retrieve(subscription_id: str) -> dict[str, str]:
            assert subscription_id == "sub_verified"
            return {"status": "active"}

    StripeStub = SimpleNamespace(
        api_key="",
        checkout=SimpleNamespace(Session=CheckoutSession),
        Subscription=Subscription,
    )

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_value")
    monkeypatch.setitem(__import__("sys").modules, "stripe", StripeStub)
    result = verify_checkout_entitlement("cs_test_verified")
    assert result == {"active": True, "status": "active", "plan": "yearly"}

