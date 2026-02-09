from app.routers.alerts import router as alerts_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.ingest import router as ingest_router
from app.routers.ml import router as ml_router
from app.routers.search import router as search_router
from app.routers.whatsapp import router as whatsapp_router

__all__ = [
    "alerts_router",
    "auth_router",
    "dashboard_router",
    "health_router",
    "ingest_router",
    "ml_router",
    "search_router",
    "whatsapp_router",
]
