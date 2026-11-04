from fastapi import APIRouter, Depends
from app.services.observability_service import ObservabilityService
from app.services.dependencies import get_observability_service
from app.auth.dependencies import require_role

router = APIRouter(prefix="/observability", tags=["observability"], dependencies=[Depends(require_role("ROLE_ADMIN"))])

@router.get("/metrics")
async def get_metrics(service: ObservabilityService = Depends(get_observability_service)):
    return service.snapshot()
