from __future__ import annotations

import os
from typing import Literal
from urllib.parse import urlparse


BillingPlan = Literal["monthly", "yearly"]


class BillingConfigurationError(RuntimeError):
    pass


def resolve_public_origin(request_origin: str) -> str:
    configured = os.getenv("APP_URL", "").strip().rstrip("/")
    if configured:
        parsed = urlparse(configured)
        if parsed.scheme != "https" or not parsed.netloc:
            raise BillingConfigurationError("APP_URL must be a valid HTTPS origin.")
        return configured

    parsed = urlparse(request_origin)
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}:
        return request_origin.rstrip("/")
    raise BillingConfigurationError("APP_URL is required before subscription checkout can be enabled.")


def create_checkout_session(plan: BillingPlan, origin: str) -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    price_ids = {
        "monthly": os.getenv("STRIPE_PRICE_MONTHLY", "").strip(),
        "yearly": os.getenv("STRIPE_PRICE_YEARLY", "").strip(),
    }
    if not secret_key or not price_ids[plan]:
        raise BillingConfigurationError("Subscription checkout is not configured yet.")
    public_origin = resolve_public_origin(origin)

    import stripe

    stripe.api_key = secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_ids[plan], "quantity": 1}],
        allow_promotion_codes=True,
        success_url=f"{public_origin}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{public_origin}/?checkout=cancelled",
        metadata={"product": "listing-launch-auditor", "plan": plan},
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a checkout URL.")
    return session.url


def verify_checkout_entitlement(session_id: str) -> dict[str, str | bool]:
    if not session_id.startswith("cs_") or len(session_id) > 256:
        return {"active": False, "reason": "invalid_session"}

    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise BillingConfigurationError("Subscription verification is not configured yet.")

    import stripe

    stripe.api_key = secret_key
    session = stripe.checkout.Session.retrieve(session_id)
    if session.get("mode") != "subscription" or session.get("status") != "complete":
        return {"active": False, "reason": "checkout_incomplete"}

    subscription_id = session.get("subscription")
    if not subscription_id:
        return {"active": False, "reason": "subscription_missing"}

    subscription = stripe.Subscription.retrieve(subscription_id)
    status = str(subscription.get("status", ""))
    active = status in {"active", "trialing"}
    return {
        "active": active,
        "status": status or "unknown",
        "plan": str(session.get("metadata", {}).get("plan", "pro")),
    }

