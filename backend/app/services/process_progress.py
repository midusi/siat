import os
import re
from pathlib import Path

_PROGRESS_RE = re.compile(r"Progreso:\s*(\d+)%")


def latest_progress(text: str) -> int | None:
    found = _PROGRESS_RE.findall(text or "")
    if not found:
        return None
    return max(0, min(100, int(found[-1])))


def tail_progress(path: Path, size: int = 8192) -> int | None:
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            end = handle.tell()
            handle.seek(max(0, end - size))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    return latest_progress(text)
