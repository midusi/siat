# services/inference_service.py
from sqlalchemy.orm import sessionmaker

from app.models import Inference
import datetime

class InferenceService:
    def __init__(self, db: sessionmaker):
        self.db = db

    def create_inference(self, task_id: int, url_counts: str, url_undetermined: str, url_determined: str) -> Inference:
      inference_obj = Inference(
          task_id=task_id,
          url_transition_counts=url_counts,
          url_transition_undetermined=url_undetermined,
          url_video_processed=url_determined,
          inferred_at=datetime.datetime.now()
      )
      self.db.add(inference_obj)
      self.db.flush()
      return inference_obj