from app.domain.entities import TaskStatusHistory
from app.ports.uow import UnitOfWork


class TaskStatusHistoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_current_by_task(self, task_id: int) -> TaskStatusHistory | None:
        return self.uow.status_histories.get_current(task_id)
