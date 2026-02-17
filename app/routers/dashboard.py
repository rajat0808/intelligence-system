from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse

from app.core.dashboard_auth import (
    dashboard_auth_enabled,
    redirect_if_unauthenticated,
    require_login_api,
)
from app.services.dashboard_service import inventory_by_status, store_danger_summary

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
def store_wise_danger_summary(
    request: Request,
    status: str | None = Query(None, description="Status filters (comma-separated)"),
    query: str | None = Query(None, description="Store search query"),
):
    require_login_api(request)
    return store_danger_summary(status_filters=status, store_query=query)


@router.get("/inventory-by-status")
def inventory_status_items(
    request: Request,
    status: str | None = Query(None, description="Status filters (comma-separated)"),
    query: str | None = Query(None, description="Store search query"),
    store_id: int | None = Query(None, description="Exact store id"),
    limit: int = Query(200, ge=1, le=2000, description="Max records to return"),
):
    require_login_api(request)
    return inventory_by_status(
        status_filters=status,
        store_query=query,
        store_id=store_id,
        limit=limit,
    )
