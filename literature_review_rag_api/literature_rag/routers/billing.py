"""Stripe billing router.

Handles subscription checkout, the Stripe customer portal, and the webhook
that syncs subscription state back into `User.plan_tier`.

Stripe is configured lazily (read env at call time, not at import) so tests
can monkeypatch `stripe.api_key` / `stripe.checkout.Session.create` etc.
cleanly without needing a real key to import this module.
"""

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import User, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Billing"])

SUCCESS_URL = "https://humbowo.com/settings/billing?status=success"
CANCEL_URL = "https://humbowo.com/settings/billing?status=cancelled"

# Stripe subscription tier -> internal plan_tier mapping.
# Pro subscription -> 'pro'; Team subscription -> 'enterprise' (a dedicated
# 'team' tier is a later refinement; see phase3c-billing plan).
PLAN_TO_TIER = {
    "pro": "pro",
    "team": "enterprise",
}


def _configure_stripe() -> str:
    """Read STRIPE_SECRET_KEY from env and configure stripe.api_key.

    Called at the top of every route handler (never at import time) so
    tests can patch the environment/stripe module per-test.
    """
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured (STRIPE_SECRET_KEY unset)"
        )
    stripe.api_key = secret_key
    return secret_key


class CheckoutRequest(BaseModel):
    plan: str = Field(..., description="'pro' or 'team'")
    seats: Optional[int] = Field(default=None, ge=1, le=1000, description="Team seats (min 3)")
    academic: bool = Field(default=False, description="Apply the academic/NGO coupon")

    @field_validator("plan")
    @classmethod
    def _validate_plan(cls, v: str) -> str:
        if v not in ("pro", "team"):
            raise ValueError("plan must be 'pro' or 'team'")
        return v


def _price_for_plan(plan: str) -> str:
    if plan == "pro":
        price_id = os.getenv("STRIPE_PRICE_PRO")
    else:
        price_id = os.getenv("STRIPE_PRICE_TEAM")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Billing is not configured (price for plan '{plan}' unset)"
        )
    return price_id


def _get_or_create_customer(db: Session, user: User) -> str:
    """Return the user's Stripe customer id, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)}
    )
    user.stripe_customer_id = customer["id"] if isinstance(customer, dict) else customer.id
    db.commit()
    db.refresh(user)
    return user.stripe_customer_id


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout Session for a subscription plan."""
    _configure_stripe()

    seats = 1
    if request.plan == "team":
        seats = request.seats if request.seats is not None else 3
        if seats < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team plan requires a minimum of 3 seats"
            )
        if seats > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team plan supports a maximum of 100 seats"
            )

    price_id = _price_for_plan(request.plan)

    try:
        customer_id = _get_or_create_customer(db, current_user)

        metadata = {"user_id": str(current_user.id), "plan": request.plan}

        session_kwargs = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": seats}],
            "success_url": SUCCESS_URL,
            "cancel_url": CANCEL_URL,
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
        }

        if request.academic:
            coupon = os.getenv("STRIPE_COUPON_ACADEMIC")
            if coupon:
                session_kwargs["discounts"] = [{"coupon": coupon}]

        session = stripe.checkout.Session.create(**session_kwargs)
        url = session["url"] if isinstance(session, dict) else session.url
        return {"url": url}

    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create checkout session"
        )
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Checkout failed"
        )


@router.post("/portal")
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe billing-portal session for the user's stored customer."""
    _configure_stripe()

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Subscribe to a plan first."
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=SUCCESS_URL,
        )
        url = portal_session["url"] if isinstance(portal_session, dict) else portal_session.url
        return {"url": url}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create billing portal session"
        )
    except Exception as e:
        logger.error(f"Portal session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portal session failed"
        )


@router.get("/status")
async def get_billing_status(
    current_user: User = Depends(get_current_user)
):
    """Return the current user's plan tier and Stripe linkage state."""
    return {
        "plan_tier": current_user.plan_tier,
        "has_customer": bool(current_user.stripe_customer_id),
        "subscription_id": current_user.stripe_subscription_id,
    }


def _apply_plan_from_metadata(db: Session, metadata: dict, subscription_id: Optional[str]) -> None:
    """Set User.plan_tier + stripe_subscription_id from event metadata."""
    user_id = metadata.get("user_id")
    plan = metadata.get("plan")
    if not user_id or not plan:
        logger.warning(f"Webhook event metadata missing user_id/plan: {metadata}")
        return

    tier = PLAN_TO_TIER.get(plan)
    if not tier:
        logger.warning(f"Webhook event has unrecognized plan '{plan}'")
        return

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        logger.warning(f"Webhook event references unknown user_id={user_id}")
        return

    user.plan_tier = tier
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    db.commit()
    logger.info(f"Billing: user {user_id} plan_tier -> {tier} (subscription={subscription_id})")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events, verifying the signature.

    No auth dependency: Stripe calls this directly with a signed body
    instead of a session/bearer token. Must also be exempt from the app's
    CSRF middleware (a cookie-less POST is already skipped by that
    middleware, but the path is additionally whitelisted defensively).
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook is not configured (STRIPE_WEBHOOK_SECRET unset)"
        )

    _configure_stripe()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        logger.warning("Webhook payload could not be parsed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type = event["type"] if isinstance(event, dict) else event.type
    data_object = event["data"]["object"] if isinstance(event, dict) else event.data.object

    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    if event_type == "checkout.session.completed":
        metadata = _get(data_object, "metadata", {}) or {}
        subscription_id = _get(data_object, "subscription")
        _apply_plan_from_metadata(db, dict(metadata), subscription_id)
        logger.info(f"Webhook handled: {event_type}")

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        metadata = _get(data_object, "metadata", {}) or {}
        sub_status = _get(data_object, "status")
        subscription_id = _get(data_object, "id")
        if sub_status == "active":
            _apply_plan_from_metadata(db, dict(metadata), subscription_id)
            logger.info(f"Webhook handled: {event_type} (status=active)")
        else:
            # past_due/unpaid/incomplete etc: leave tier as-is, just log.
            logger.info(f"Webhook ignored (no tier change): {event_type} (status={sub_status})")

    elif event_type == "customer.subscription.deleted":
        metadata = _get(data_object, "metadata", {}) or {}
        user_id = metadata.get("user_id") if metadata else None
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.plan_tier = "free"
                user.stripe_subscription_id = None
                db.commit()
                logger.info(f"Webhook handled: {event_type} -> user {user_id} plan_tier -> free")
            else:
                logger.warning(f"Webhook {event_type}: unknown user_id={user_id}")
        else:
            logger.warning(f"Webhook {event_type}: metadata missing user_id")

    else:
        logger.info(f"Webhook ignored (unhandled type): {event_type}")

    return {"received": True}
