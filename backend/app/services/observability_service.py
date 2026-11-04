from typing import Any, Dict

from app.observability.metrics import get_counters
from app.ports.uow import UnitOfWork


class ObservabilityService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def snapshot(self) -> Dict[str, Any]:
        data: Dict[str, Any] = get_counters().copy()
        data["active_users"] = len(self.uow.users.list_all(active=True))
        return data
