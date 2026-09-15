from app.domain.entities import TaskStatus
from app.ports.uow import UnitOfWork


class TaskStatusService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_by_id(self, task_status_id: str) -> TaskStatus | None:
        return self.uow.task_statuses.get(task_status_id)
