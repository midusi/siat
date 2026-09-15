from app.ports.uow import UnitOfWork


class RouteService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
