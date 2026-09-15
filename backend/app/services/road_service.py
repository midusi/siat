from app.domain.entities import Road
from app.enums.road_direction import RoadDirection
from app.ports.uow import UnitOfWork


class RoadService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def find_by_fields(self, **filters) -> list[Road]:
        video_id = filters.get("video_id")
        if video_id is None:
            return []
        return self.uow.roads.list_by_video(video_id)

    def create(self, number: int, direction: RoadDirection, polygon, video_id: int, name: str | None = None) -> Road:
        direction_value = direction.value if isinstance(direction, RoadDirection) else str(direction)
        return Road(
            name=name if name is not None and len(name) > 0 else f"Vía {number}",
            direction=direction_value,
            polygon=polygon,
            video_id=video_id,
        )
