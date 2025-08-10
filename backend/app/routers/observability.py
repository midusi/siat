from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db_session
from app.observability.metrics import snapshot
from app.auth.dependencies import require_role

router = APIRouter(prefix="/observability", tags=["observability"], dependencies=[Depends(require_role("ROLE_ADMIN"))])

@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db_session)):
    return snapshot(db)
