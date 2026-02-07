import importlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.config import Settings, get_settings
from app.database import Base, engine, ensure_sqlite_schema
from app.services.excel_watch import ExcelWatchService, ensure_datasource_dir

from app.api.dashboard import router as dashboard_router
from app.api.search import router as search_router
from app.api.whatsapp import router as whatsapp_router
from app.api.ml import router as ml_router
from app.api.alerts import router as alerts_router


def _import_models():
    for module_name in (
        "app.models.daily_snapshot",
        "app.models.delivery_logs",
        "app.models.inventory",
        "app.models.lifecycle",
        "app.models.product",
        "app.models.sales",
        "app.models.stores",
    ):
        importlib.import_module(module_name)


_import_models()
Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

settings: Settings = get_settings()
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


app = FastAPI(title="Inventory Intelligence Platform", lifespan=lifespan)

app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(whatsapp_router)
app.include_router(ml_router)
app.include_router(alerts_router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard", status_code=302)
