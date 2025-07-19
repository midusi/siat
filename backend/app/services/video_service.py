# services/video_service.py
from fastapi import UploadFile
from sqlalchemy.orm import sessionmaker
from pymediainfo import MediaInfo
import tempfile
import shutil


class VideoService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_metadata_video(self, file: UploadFile) -> dict:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            media_info = MediaInfo.parse(tmp_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    duration = int(track.duration / 1000) if track.duration else None
                    fps = float(track.frame_rate) if track.frame_rate else None
                    width = int(track.width) if track.width else None
                    height = int(track.height) if track.height else None

                    return {
                        "duration": duration, #in secords
                        "fps": fps,
                        "width": width,
                        "height": height
                    }
        except Exception as e:
            file.file.close()
            raise ValueError(f"No se pudo obtener la duración del video: {e}")
        finally:
            file.file.seek(0)
