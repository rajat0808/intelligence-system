import importlib
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.core.constants import DEFAULT_DASHBOARD_PATH, STATIC_DIR, TEMPLATES_DIR
from app.core.logging import setup_logging
from app.database import Base, engine, ensure_sqlite_schema
from app.routers import (
    alerts_router,
    auth_router,
    dashboard_router,
    health_router,
    ingest_router,
    ml_router,
    products_router,
    search_router,
    whatsapp_router,
)
from app.services.ingestion_service import ExcelWatchService, ensure_datasource_dir


def _import_models():
    for module_name in (
        "app.models.alert",
        "app.models.daily_snapshot",
        "app.models.delivery_logs",
        "app.models.inventory",
        "app.models.job_log",
        "app.models.lifecycle",
        "app.models.price_history",
        "app.models.product",
        "app.models.risk_log",
        "app.models.sales",
        "app.models.stores",
    ):
        importlib.import_module(module_name)


setup_logging()
settings: Settings = get_settings()

_import_models()
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

excel_watch_service = ExcelWatchService(
    watch_dir=settings.EXCEL_DATASOURCE_DIR,
    poll_seconds=settings.EXCEL_POLL_SECONDS,
    sheets=settings.EXCEL_IMPORT_SHEETS,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_datasource_dir(settings.EXCEL_DATASOURCE_DIR)
    if settings.EXCEL_AUTO_IMPORT:
        excel_watch_service.start()
    try:
        yield
    finally:
        excel_watch_service.stop()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.DASHBOARD_SESSION_SECRET or settings.JWT_SECRET or secrets.token_urlsafe(32),
    session_cookie=settings.DASHBOARD_SESSION_COOKIE,
    same_site="lax",
    https_only=settings.ENVIRONMENT.lower() != "local",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(ml_router)
app.include_router(alerts_router)
app.include_router(products_router)
app.include_router(search_router)
app.include_router(whatsapp_router)


@app.get("/")
def root():
    return RedirectResponse(url=DEFAULT_DASHBOARD_PATH, status_code=302)


__all__ = ["app", "root"]
