import base64
import tempfile
import shutil
from fastapi import UploadFile
from app.ports.storage import ObjectStorage


class VideoService:
    def __init__(self, storage: ObjectStorage):
        self.storage = storage

    def get_metadata_video(self, file: UploadFile) -> dict:
        from pymediainfo import MediaInfo
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

    def get_frame(self, video_key: str, frame_number: int) -> str:
        import cv2
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            temp_path = tmp.name

            try:
                self.storage.download(temp_path, video_key)
            except Exception as e:
                raise ValueError(f"Could not download video '{video_key}' from bucket: {e}")

            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open temporary video file: {temp_path}")

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                raise ValueError(f"Cannot read frame {frame_number} from video: {video_key}")

            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            return jpg_as_text

    def get_video_stream(self, video_key: str):
        return self.storage.stream_object(video_key)

    def get_metadata_from_s3(self, object_key: str) -> dict:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name

        try:
            from pymediainfo import MediaInfo
            self.storage.download(tmp_path, object_key)

            media_info = MediaInfo.parse(tmp_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    duration = int(track.duration / 1000) if track.duration else None
                    fps = float(track.frame_rate) if track.frame_rate else None
                    width = int(track.width) if track.width else None
                    height = int(track.height) if track.height else None

                    return {
                        "duration": duration,
                        "fps": fps,
                        "width": width,
                        "height": height
                    }

            raise ValueError("No se encontró track de video en el archivo")
        except Exception as e:
            raise ValueError(f"No se pudo obtener metadata del video: {e}")
        finally:
            try:
                import os
                os.unlink(tmp_path)
            except:
                pass
