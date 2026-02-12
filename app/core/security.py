from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

from app.config import get_settings


def _load_api_keys() -> set[str]:
    settings = get_settings()
    keys = set()
    if settings.FOUNDER_API_KEY:
        keys.add(settings.FOUNDER_API_KEY.strip())
    if settings.API_KEYS:
        for value in settings.API_KEYS.split(","):
            value = value.strip()
            if value:
                keys.add(value)
    return keys


def _get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _decode_jwt(token: str) -> dict:
    settings = get_settings()
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT auth is not configured",
        )
    try:
        import jwt  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyJWT is required for JWT auth",
        ) from exc

    options = {"verify_aud": bool(settings.JWT_AUDIENCE)}
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT",
        ) from exc


def authenticate_request(
    api_key: Optional[str],
    authorization: Optional[str],
    *,
    require_auth: bool = False,
) -> Optional[dict]:
    settings = get_settings()
    keys = _load_api_keys()

    if settings.JWT_REQUIRED:
        require_auth = True

    if api_key and api_key in keys and not settings.JWT_REQUIRED:
        return {"auth_type": "api_key"}

    token = _get_bearer_token(authorization)
    if token:
        try:
            payload = _decode_jwt(token)
            return {"auth_type": "jwt", "payload": payload}
        except HTTPException:
            if settings.JWT_REQUIRED:
                raise

    if (require_auth or keys or settings.JWT_REQUIRED) and (
        keys or settings.JWT_SECRET or settings.JWT_REQUIRED
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return None
