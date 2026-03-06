import importlib
import logging
import secrets
import threading
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
from app.scheduler.job_scheduler import (
    DailyJobScheduler,
    SchedulerConfig,
    ensure_scheduler_schema,
    parse_time,
)
from app.services.alert_service import run_alerts
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
logger = logging.getLogger(__name__)


def _resolve_session_secret(app_settings: Settings) -> str:
    secret = app_settings.DASHBOARD_SESSION_SECRET or app_settings.JWT_SECRET
    if secret:
        return secret
    if app_settings.ENVIRONMENT.lower() == "local":
        return secrets.token_urlsafe(32)
    raise RuntimeError(
        "ENVIRONMENT=production requires DASHBOARD_SESSION_SECRET or JWT_SECRET so "
        "dashboard sessions persist across restarts."
    )

_import_models()
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

excel_watch_service = ExcelWatchService(
    watch_dir=settings.EXCEL_DATASOURCE_DIR,
    poll_seconds=settings.EXCEL_POLL_SECONDS,
    sheets=settings.EXCEL_IMPORT_SHEETS,
)


def _run_alert_job() -> None:
    stats = run_alerts(send_notifications=True)
    logger.info(
        "Alert workflow completed. snapshots=%s alerts=%s",
        stats.get("snapshots"),
        stats.get("alerts"),
    )


def _build_daily_scheduler(app_settings: Settings) -> DailyJobScheduler:
    config = SchedulerConfig(
        job_name="daily-intelligence",
        run_after_time=parse_time(app_settings.SCHEDULER_RUN_AFTER),
        poll_seconds=app_settings.SCHEDULER_POLL_SECONDS,
        heartbeat_seconds=app_settings.SCHEDULER_HEARTBEAT_SECONDS,
        stale_seconds=app_settings.SCHEDULER_STALE_SECONDS,
        retry_seconds=app_settings.SCHEDULER_RETRY_SECONDS,
        max_retries=app_settings.SCHEDULER_MAX_RETRIES,
        timezone_mode=app_settings.SCHEDULER_TZ,
    )
    return DailyJobScheduler(config=config, job_func=_run_alert_job)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler: DailyJobScheduler | None = None
    scheduler_thread: threading.Thread | None = None

    ensure_datasource_dir(settings.EXCEL_DATASOURCE_DIR)
    if settings.EXCEL_AUTO_IMPORT:
        excel_watch_service.start()

    if settings.SCHEDULER_ENABLED:
        ensure_scheduler_schema()
        scheduler = _build_daily_scheduler(settings)
        if settings.SCHEDULER_RUN_ON_STARTUP:
            try:
                logger.info("Running alert workflow on server startup.")
                _run_alert_job()
            except Exception:
                logger.exception("Startup alert workflow failed.")
        scheduler_thread = threading.Thread(
            target=scheduler.run_forever,
            name="daily-intelligence-scheduler",
            daemon=True,
        )
        scheduler_thread.start()

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.stop()
        if scheduler_thread is not None and scheduler_thread.is_alive():
            scheduler_thread.join(timeout=max(1, settings.SCHEDULER_POLL_SECONDS) + 2)
        excel_watch_service.stop()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.add_middleware(
    SessionMiddleware,
    secret_key=_resolve_session_secret(settings),
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
