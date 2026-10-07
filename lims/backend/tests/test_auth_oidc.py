import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import auth
from app.core.config import AuthMode, get_settings
from app.core.errors import PermissionDenied
from app.modules.identity import service as identity
from app.modules.identity.models import Role

ISSUER = "https://login.example.test/tenant/v2.0"
AUDIENCE = "lims-api"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(**claims) -> str:
    now = int(time.time())
    body = {"iss": ISSUER, "aud": AUDIENCE, "iat": now, "exp": now + 600, "sub": "s", **claims}
    return jwt.encode(body, KEY, algorithm="RS256")


@pytest.fixture
def oidc(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", AuthMode.OIDC)
    monkeypatch.setattr(settings, "oidc_issuer", ISSUER)
    monkeypatch.setattr(settings, "oidc_audience", AUDIENCE)
    fake = SimpleNamespace(
        get_signing_key_from_jwt=lambda _t: SimpleNamespace(key=KEY.public_key())
    )
    monkeypatch.setattr(auth, "_jwks_client", lambda: fake)


@pytest.fixture
def scientist(db: Session):
    return identity.create_user(
        db,
        actor=None,
        username="oidc.cs",
        display_name="O",
        oidc_subject="oid-123",
        roles=[Role.CASE_SCIENTIST],
    )


@pytest.mark.urs("WF-01.02")
def test_bearer_token_maps_to_lims_account(client: TestClient, oidc, scientist) -> None:
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token(oid='oid-123')}"})
    assert r.status_code == 200 and r.json()["username"] == "oidc.cs"
    # Dev header is ignored in OIDC mode.
    assert client.get("/api/me", headers={"X-Dev-User": "oidc.cs"}).status_code == 401


def test_invalid_tokens_are_rejected(client: TestClient, oidc, scientist) -> None:
    for bad in (
        token(oid="oid-123", aud="other"),
        token(oid="oid-123", iss="https://evil"),
        token(oid="oid-123", exp=int(time.time()) - 10),
    ):
        assert client.get("/api/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401
    r = client.get("/api/me", headers={"Authorization": f"Bearer {token(oid='unknown')}"})
    assert r.status_code == 403


def test_reauthentication_must_be_recent_and_for_the_same_person(oidc, scientist) -> None:
    now = int(time.time())
    proof = auth.get_reauth_proof(scientist, x_reauth_token=token(oid="oid-123", auth_time=now))
    assert proof.user_id == scientist.id
    with pytest.raises(PermissionDenied):
        auth.get_reauth_proof(scientist, x_reauth_token=token(oid="someone-else", auth_time=now))
    with pytest.raises(PermissionDenied):
        auth.get_reauth_proof(scientist, x_reauth_token=token(oid="oid-123"))
    old = auth.get_reauth_proof(
        scientist, x_reauth_token=token(oid="oid-123", auth_time=now - 3600)
    )
    assert (time.time() - old.authenticated_at.timestamp()) > 3000  # sign() will refuse this
