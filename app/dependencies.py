from typing import Optional

from fastapi import Header

from app.core.security import authenticate_request
from app.database.session import get_db


def require_auth(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_alt: Optional[str] = Header(None, alias="api-key"),
    authorization: Optional[str] = Header(None),
):
    api_key_value = api_key or api_key_alt
    return authenticate_request(
        api_key=api_key_value,
        authorization=authorization,
        require_auth=True,
    )


__all__ = ["get_db", "require_auth"]
