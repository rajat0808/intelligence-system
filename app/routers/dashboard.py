from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse

from app.core.dashboard_auth import (
    dashboard_auth_enabled,
    redirect_if_unauthenticated,
    require_login_api,
)
from app.services.dashboard_service import store_danger_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request):
    redirect = redirect_if_unauthenticated(request)
    if redirect:
        return redirect
    templates = request.app.state.templates
    summary = jsonable_encoder(store_danger_summary())
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "dashboard_data": summary,
            "auth_enabled": dashboard_auth_enabled(),
        },
    )


@router.get("/store-danger-summary")
def store_wise_danger_summary(request: Request):
    require_login_api(request)
    return store_danger_summary()
