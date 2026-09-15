import datetime

from app.domain.entities import Inference
from app.ports.uow import UnitOfWork


class InferenceService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def create_inference(
        self,
        task_id: int,
        transition_counts: str,
        transition_undetermined: str,
        transition_determined: str,
        url_data_obj_history: str,
        url_video_processed: str,
    ) -> Inference:
        inference_obj = Inference(
            task_id=task_id,
            transition_counts=transition_counts,
            transition_undetermined=transition_undetermined,
            transition_determined=transition_determined,
            url_data_obj_history=url_data_obj_history,
            url_video_processed=url_video_processed,
            inferred_at=datetime.datetime.now(),
        )
        self.uow.inferences.add(inference_obj)
        self.uow.flush()
        return inference_obj
