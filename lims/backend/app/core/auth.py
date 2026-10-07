"""Authentication: each person signs in with their own account (WF-01.02).

Production uses OIDC bearer tokens (e.g. Microsoft Entra ID), validated against
the issuer's JWKS and mapped to a LIMS user by subject claim. Development and
test use an `X-Dev-User` header; settings refuse dev auth in production.

E-signatures need fresh proof of identity: an ID token whose `auth_time` is
recent (OIDC, requested with prompt=login / max_age=0), passed as
`X-Reauth-Token`.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import AuthMode, get_settings
from app.core.db import get_db
from app.core.documents import ReauthProof
from app.core.errors import DomainError, PermissionDenied
from app.modules.identity.models import Role, User


class Unauthenticated(DomainError):
    status_code = 401
    code = "unauthenticated"


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    url = get_settings().oidc_jwks_url
    if not url:
        raise Unauthenticated("OIDC is not configured")
    return jwt.PyJWKClient(url, cache_keys=True)


def decode_oidc_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        key = _jwks_client().get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid or expired sign-in token") from exc
    return claims


def _user_by(session: Session, **filters: str) -> User | None:
    return session.execute(select(User).filter_by(**filters)).scalar_one_or_none()


def _require_active(user: User | None) -> User:
    if user is None:
        raise PermissionDenied("No LIMS account exists for this sign-in")
    if not user.is_active:
        raise PermissionDenied("This LIMS account is disabled")
    return user


def get_current_user(
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user: Annotated[str | None, Header()] = None,
) -> User:
    settings = get_settings()
    if settings.auth_mode == AuthMode.DEV:
        if not x_dev_user:
            raise Unauthenticated("Sign in required (X-Dev-User header in dev mode)")
        return _require_active(_user_by(session, username=x_dev_user))

    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthenticated("Sign in required")
    claims = decode_oidc_token(authorization.split(" ", 1)[1])
    subject = claims.get(settings.oidc_subject_claim)
    if not subject:
        raise Unauthenticated("Token has no subject claim")
    return _require_active(_user_by(session, oidc_subject=str(subject)))


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_reauth_proof(
    user: CurrentUser,
    x_reauth_token: Annotated[str | None, Header()] = None,
    x_dev_reauth: Annotated[str | None, Header()] = None,
) -> ReauthProof:
    settings = get_settings()
    if settings.auth_mode == AuthMode.DEV:
        if x_dev_reauth != user.username:
            raise PermissionDenied("Re-authenticate to sign (X-Dev-Reauth header in dev mode)")
        return ReauthProof(user.id, datetime.now(UTC))

    if not x_reauth_token:
        raise PermissionDenied("Re-authenticate to sign")
    claims = decode_oidc_token(x_reauth_token)
    if str(claims.get(settings.oidc_subject_claim)) != user.oidc_subject:
        raise PermissionDenied("Re-authentication was for a different account")
    auth_time = claims.get("auth_time")
    if not isinstance(auth_time, int | float):
        raise PermissionDenied("Re-authentication token has no auth_time")
    return ReauthProof(user.id, datetime.fromtimestamp(auth_time, UTC))


Reauth = Annotated[ReauthProof, Depends(get_reauth_proof)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if not user.has_role(*roles):
            raise PermissionDenied("Requires one of: " + ", ".join(sorted(r.value for r in roles)))
        return user

    return dependency
