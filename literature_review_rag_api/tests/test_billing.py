"""Stripe billing: checkout, portal, status, and webhook plan sync.

Stripe SDK calls are monkeypatched — no network access, no real keys needed.

Users are created directly via UserCRUD + a minted JWT (see test_public_workspaces.py
for precedent) rather than through /api/auth/register|login: those two endpoints
share a single 15-req/60s rate-limit bucket keyed by client IP across the WHOLE
test session, and other test files already spend nearly all of that budget
(see the note atop test_workspace_access.py). Going through real HTTP auth here
would blow the shared budget and make unrelated test files flaky.
"""
import uuid

import stripe
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_user_client(email_prefix: str):
    """Create a user directly in the DB and mint a bearer token for it.

    Bypasses the rate-limited /api/auth/register and /api/auth/login routes.
    """
    from literature_rag.api import app
    from literature_rag.database import get_db_session, UserCRUD
    from literature_rag.auth import create_access_token

    email = f"{email_prefix}-{uuid.uuid4().hex[:8]}@test.local"
    db = get_db_session()
    user = UserCRUD.create(db, email=email, password_hash="x")
    token = create_access_token(user.id, user.email)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers, user.id


def _stripe_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro_dummy")
    monkeypatch.setenv("STRIPE_PRICE_TEAM", "price_team_dummy")
    monkeypatch.setenv("STRIPE_COUPON_ACADEMIC", "ACADEMIC50")


# ============================================================================
# Checkout
# ============================================================================

def test_checkout_requires_auth(monkeypatch):
    _stripe_env(monkeypatch)
    from literature_rag.api import app
    client = TestClient(app)
    r = client.post("/api/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 401


def test_pro_checkout_returns_url_and_persists_customer_id(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, user_id = _make_user_client("bill-pro")

    fake_customer = MagicMock(id="cus_123")
    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_123")

    with patch("stripe.Customer.create", return_value=fake_customer) as mock_customer, \
         patch("stripe.checkout.Session.create", return_value=fake_session) as mock_session:
        r = client.post("/api/billing/checkout", json={"plan": "pro"}, headers=h)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"] == "https://checkout.stripe.com/pay/cs_test_123"
    mock_customer.assert_called_once()
    mock_session.assert_called_once()

    kwargs = mock_session.call_args.kwargs
    assert kwargs["customer"] == "cus_123"
    assert kwargs["mode"] == "subscription"
    assert kwargs["line_items"] == [{"price": "price_pro_dummy", "quantity": 1}]
    assert kwargs["metadata"] == {"user_id": str(user_id), "plan": "pro"}
    assert kwargs["subscription_data"]["metadata"]["plan"] == "pro"
    assert "discounts" not in kwargs

    # Persisted customer id
    from literature_rag.database import get_db_session, UserCRUD
    db2 = get_db_session()
    user = UserCRUD.get_by_id(db2, user_id)
    assert user.stripe_customer_id == "cus_123"

    # Second checkout call reuses the stored customer, doesn't recreate
    fake_session2 = MagicMock(url="https://checkout.stripe.com/pay/cs_test_456")
    with patch("stripe.Customer.create") as mock_customer2, \
         patch("stripe.checkout.Session.create", return_value=fake_session2) as mock_session2:
        r2 = client.post("/api/billing/checkout", json={"plan": "pro"}, headers=h)
    assert r2.status_code == 200
    mock_customer2.assert_not_called()
    assert mock_session2.call_args.kwargs["customer"] == "cus_123"


def test_team_checkout_seats_below_minimum_returns_400(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-team-lowseat")

    with patch("stripe.Customer.create", return_value=MagicMock(id="cus_team")), \
         patch("stripe.checkout.Session.create") as mock_session:
        r = client.post("/api/billing/checkout", json={"plan": "team", "seats": 2}, headers=h)

    assert r.status_code == 400, r.text
    mock_session.assert_not_called()


def test_team_checkout_default_seats_and_valid_seats(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-team-ok")

    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_team")
    with patch("stripe.Customer.create", return_value=MagicMock(id="cus_team2")), \
         patch("stripe.checkout.Session.create", return_value=fake_session) as mock_session:
        r = client.post("/api/billing/checkout", json={"plan": "team", "seats": 5}, headers=h)

    assert r.status_code == 200, r.text
    kwargs = mock_session.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_team_dummy", "quantity": 5}]


def test_academic_flag_passes_coupon(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-academic")

    fake_session = MagicMock(url="https://checkout.stripe.com/pay/cs_academic")
    with patch("stripe.Customer.create", return_value=MagicMock(id="cus_academic")), \
         patch("stripe.checkout.Session.create", return_value=fake_session) as mock_session:
        r = client.post(
            "/api/billing/checkout",
            json={"plan": "pro", "academic": True},
            headers=h
        )

    assert r.status_code == 200, r.text
    kwargs = mock_session.call_args.kwargs
    assert kwargs["discounts"] == [{"coupon": "ACADEMIC50"}]


# ============================================================================
# Portal
# ============================================================================

def test_portal_requires_customer(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-noportal")
    r = client.post("/api/billing/portal", headers=h)
    assert r.status_code == 400


def test_portal_session_created_for_existing_customer(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-portal")

    with patch("stripe.Customer.create", return_value=MagicMock(id="cus_portal")), \
         patch("stripe.checkout.Session.create", return_value=MagicMock(url="https://x/y")):
        client.post("/api/billing/checkout", json={"plan": "pro"}, headers=h)

    fake_portal = MagicMock(url="https://billing.stripe.com/session/abc")
    with patch("stripe.billing_portal.Session.create", return_value=fake_portal) as mock_portal:
        r = client.post("/api/billing/portal", headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["url"] == "https://billing.stripe.com/session/abc"
    assert mock_portal.call_args.kwargs["customer"] == "cus_portal"


# ============================================================================
# Status
# ============================================================================

def test_billing_status_defaults(monkeypatch):
    _stripe_env(monkeypatch)
    client, h, _ = _make_user_client("bill-status")
    r = client.get("/api/billing/status", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"plan_tier": "free", "has_customer": False, "subscription_id": None}


def test_billing_status_requires_auth(monkeypatch):
    _stripe_env(monkeypatch)
    from literature_rag.api import app
    client = TestClient(app)
    r = client.get("/api/billing/status")
    assert r.status_code == 401


# ============================================================================
# Webhook
# ============================================================================

def test_webhook_unset_secret_returns_503(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)
    r = client.post("/api/billing/webhook", content=b"{}",
                    headers={"stripe-signature": "t=1,v1=bad"})
    assert r.status_code == 503, r.text


def test_webhook_bad_signature_returns_400(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)

    def _raise(*a, **kw):
        raise stripe.error.SignatureVerificationError("bad sig", "sig_header")

    with patch("stripe.Webhook.construct_event", side_effect=_raise):
        r = client.post("/api/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=bad"})
    assert r.status_code == 400, r.text


def test_webhook_checkout_completed_pro_flips_plan_tier(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)
    _, _, user_id = _make_user_client("webhook-pro")

    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"user_id": str(user_id), "plan": "pro"},
            "subscription": "sub_pro_123",
        }},
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        r = client.post("/api/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=ok"})
    assert r.status_code == 200, r.text

    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    user = UserCRUD.get_by_id(db, user_id)
    assert user.plan_tier == "pro"
    assert user.stripe_subscription_id == "sub_pro_123"


def test_webhook_checkout_completed_team_flips_to_enterprise(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)
    _, _, user_id = _make_user_client("webhook-team")

    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"user_id": str(user_id), "plan": "team"},
            "subscription": "sub_team_123",
        }},
    }

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        r = client.post("/api/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=ok"})
    assert r.status_code == 200, r.text

    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    user = UserCRUD.get_by_id(db, user_id)
    assert user.plan_tier == "enterprise"
    assert user.stripe_subscription_id == "sub_team_123"


def test_webhook_subscription_deleted_flips_back_to_free(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)
    _, _, user_id = _make_user_client("webhook-delete")

    # First flip to pro via completed checkout
    completed_event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "metadata": {"user_id": str(user_id), "plan": "pro"},
            "subscription": "sub_del_123",
        }},
    }
    with patch("stripe.Webhook.construct_event", return_value=completed_event):
        client.post("/api/billing/webhook", content=b"{}",
                    headers={"stripe-signature": "t=1,v1=ok"})

    deleted_event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {
            "id": "sub_del_123",
            "metadata": {"user_id": str(user_id), "plan": "pro"},
        }},
    }
    with patch("stripe.Webhook.construct_event", return_value=deleted_event):
        r = client.post("/api/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=ok"})
    assert r.status_code == 200, r.text

    from literature_rag.database import get_db_session, UserCRUD
    db = get_db_session()
    user = UserCRUD.get_by_id(db, user_id)
    assert user.plan_tier == "free"
    assert user.stripe_subscription_id is None


def test_webhook_unhandled_event_type_is_ignored(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from literature_rag.api import app
    client = TestClient(app)

    fake_event = {"type": "invoice.paid", "data": {"object": {}}}
    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        r = client.post("/api/billing/webhook", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=ok"})
    assert r.status_code == 200, r.text
