from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.config import get_settings


def dashboard_auth_enabled() -> bool:
    settings = get_settings()
    return bool(settings.DASHBOARD_USERNAME and (settings.DASHBOARD_PASSWORD or settings.DASHBOARD_PASSWORD_HASH))


def _hash_password(password: str, salt: str, rounds: int) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        rounds,
    )
    return digest.hex()


def verify_dashboard_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if not dashboard_auth_enabled():
        return False

    if not settings.DASHBOARD_USERNAME:
        return False

    username = username.strip()
    password = password.strip()

    expected_username = settings.DASHBOARD_USERNAME.strip()
    if not hmac.compare_digest(username.casefold(), expected_username.casefold()):
        return False

    if settings.DASHBOARD_PASSWORD_HASH:
        if not settings.DASHBOARD_PASSWORD_SALT:
            raise ValueError("Dashboard password salt is not configured.")
        computed = _hash_password(
            password,
            settings.DASHBOARD_PASSWORD_SALT,
            settings.DASHBOARD_PBKDF2_ROUNDS,
        )
        return hmac.compare_digest(computed, settings.DASHBOARD_PASSWORD_HASH)

    if settings.DASHBOARD_PASSWORD:
        return hmac.compare_digest(password, settings.DASHBOARD_PASSWORD.strip())

    return False


def redirect_if_unauthenticated(request: Request) -> Optional[RedirectResponse]:
    if not dashboard_auth_enabled():
        return None
    if request.session.get("user"):
        return None
    return RedirectResponse(url="/login", status_code=303)


def require_login_api(request: Request) -> None:
    if not dashboard_auth_enabled():
        return
    if request.session.get("user"):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
