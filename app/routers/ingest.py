from fastapi import APIRouter, Depends, HTTPException
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import require_auth
from app.schemas.inventory import ExcelIngestRequest
from app.services.ingestion_service import import_workbook

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/excel")
def ingest_excel(payload: ExcelIngestRequest, _auth=Depends(require_auth)):
    try:
        results = import_workbook(
            payload.path,
            sheets=payload.sheets,
            dry_run=payload.dry_run,
        )
    except (OSError, ValueError, SQLAlchemyError, InvalidFileException) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"results": results}
