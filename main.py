from fastapi import FastAPI
from app.database import Base, engine

from app.api.dashboard import router as dashboard_router
from app.api.search import router as search_router
from app.api.whatsapp import router as whatsapp_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory Intelligence Platform")

app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(search_router)
app.include_router(whatsapp_router)


@app.get("/")
def root():
    return {"status": "Inventory Intelligence API running"}
