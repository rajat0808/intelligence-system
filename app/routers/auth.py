from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.constants import DEFAULT_DASHBOARD_PATH
from app.core.dashboard_auth import dashboard_auth_enabled, verify_dashboard_credentials

router = APIRouter(tags=["Auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None, "auth_enabled": dashboard_auth_enabled()},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    templates = request.app.state.templates

    if not dashboard_auth_enabled():
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Login is not configured. Set dashboard credentials in the environment.",
                "auth_enabled": False,
            },
            status_code=400,
        )

    try:
        if verify_dashboard_credentials(username, password):
            request.session["user"] = username
            return RedirectResponse(url=DEFAULT_DASHBOARD_PATH, status_code=303)
    except ValueError as exc:
        error_message = str(exc)
    else:
        error_message = "Invalid login ID or password."

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message, "auth_enabled": True},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

