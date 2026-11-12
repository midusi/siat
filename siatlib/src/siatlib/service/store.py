"""
Persistencia de trabajos en SQLite.

Una sola conexión compartida entre la API y el worker, protegida con un lock.
Cada cambio de estado es un UPDATE condicionado al estado actual, de modo que
dos actores no puedan pisarse (p. ej. cancelar un trabajo que el worker acaba
de tomar).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .jobs import (
    InvalidTransition,
    Job,
    JobRequest,
    JobStatus,
    can_transition,
    new_job_id,
    utcnow,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    id           TEXT    NOT NULL UNIQUE,
    status       TEXT    NOT NULL,
    request      TEXT    NOT NULL,
    progress     REAL    NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TEXT    NOT NULL,
    started_at   TEXT,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_seq ON jobs (status, seq);
"""


class JobNotFound(KeyError):
    def __init__(self, job_id: str):
        super().__init__(job_id)
        self.job_id = job_id

    def __str__(self) -> str:
        return f"No existe el trabajo {self.job_id}."


class JobStore:
    """Cola FIFO de trabajos persistida en SQLite. Usar ':memory:' para tests."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        if str(db_path) != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            if str(db_path) != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Alta y consulta ---------------------------------------------------- #

    def create(self, request: JobRequest) -> Job:
        job = Job(id=new_job_id(), status=JobStatus.PENDING, request=request)
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (id, status, request, progress, created_at) VALUES (?, ?, ?, 0, ?)",
                (job.id, job.status.value, json.dumps(request.to_dict()), job.created_at.isoformat()),
            )
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFound(job_id)
        return _row_to_job(row)

    def list(self, status: Optional[JobStatus] = None, limit: int = 50) -> List[Job]:
        """Trabajos más recientes primero."""
        query = "SELECT * FROM jobs"
        params: tuple = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status.value,)
        query += " ORDER BY seq DESC LIMIT ?"
        with self._lock:
            rows = self._conn.execute(query, params + (limit,)).fetchall()
        return [_row_to_job(r) for r in rows]

    def counts(self) -> Dict[str, int]:
        with self._lock:
            rows = self._conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
        result = {s.value: 0 for s in JobStatus}
        result.update({r["status"]: r["n"] for r in rows})
        return result

    # --- Transiciones -------------------------------------------------------- #

    def claim_next(self) -> Optional[Job]:
        """Toma el PENDING más antiguo y lo pasa a PROCESSING de forma atómica."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM jobs WHERE status = ? ORDER BY seq LIMIT 1", (JobStatus.PENDING.value,)
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE jobs SET status = ?, progress = 0, started_at = ? WHERE id = ? AND status = ?",
                (JobStatus.PROCESSING.value, utcnow().isoformat(), row["id"], JobStatus.PENDING.value),
            )
        return self.get(row["id"])

    def update_progress(self, job_id: str, progress: float) -> None:
        progress = max(0.0, min(100.0, float(progress)))
        with self._lock:
            self._conn.execute(
                "UPDATE jobs SET progress = ? WHERE id = ? AND status = ?",
                (progress, job_id, JobStatus.PROCESSING.value),
            )

    def mark_done(self, job_id: str) -> Job:
        return self._transition(job_id, JobStatus.DONE, progress=100.0, finished=True)

    def mark_failed(self, job_id: str, error: str) -> Job:
        return self._transition(job_id, JobStatus.FAILED, error=error, finished=True)

    def cancel(self, job_id: str) -> Job:
        return self._transition(job_id, JobStatus.CANCELLED, finished=True)

    def requeue_interrupted(self) -> int:
        """Al arrancar: los trabajos que quedaron en PROCESSING vuelven a PENDING."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE jobs SET status = ?, progress = 0, started_at = NULL WHERE status = ?",
                (JobStatus.PENDING.value, JobStatus.PROCESSING.value),
            )
        return cur.rowcount

    def _transition(
        self,
        job_id: str,
        target: JobStatus,
        *,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        finished: bool = False,
    ) -> Job:
        current = self.get(job_id).status
        if not can_transition(current, target):
            raise InvalidTransition(job_id, current, target)

        sets = ["status = ?"]
        params: list = [target.value]
        if progress is not None:
            sets.append("progress = ?")
            params.append(progress)
        if error is not None:
            sets.append("error = ?")
            params.append(error)
        if finished:
            sets.append("finished_at = ?")
            params.append(utcnow().isoformat())

        with self._lock:
            cur = self._conn.execute(
                f"UPDATE jobs SET {', '.join(sets)} WHERE id = ? AND status = ?",
                (*params, job_id, current.value),
            )
        if cur.rowcount == 0:
            # Otro actor cambió el estado entre la lectura y el UPDATE.
            raise InvalidTransition(job_id, self.get(job_id).status, target)
        return self.get(job_id)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        status=JobStatus(row["status"]),
        request=JobRequest.from_dict(json.loads(row["request"])),
        progress=row["progress"],
        error=row["error"],
        created_at=_parse_dt(row["created_at"]),
        started_at=_parse_dt(row["started_at"]),
        finished_at=_parse_dt(row["finished_at"]),
    )
