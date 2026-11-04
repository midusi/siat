from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.schemas.notification import NotificationRequest
from app.services.notification_service import notification_manager

router = APIRouter(tags=["notifications"])

@router.get("/events")
async def events(request: Request):
    return StreamingResponse(
        notification_manager.connect(),
        media_type="text/event-stream"
    )

@router.post("/internal/notify")
async def notify(notification: NotificationRequest):
    await notification_manager.broadcast(notification.model_dump())
    return {"status": "ok"}
