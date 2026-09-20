"""Thread-safe recorder for user animation critiques and DPO/SFT preference trajectories."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.schemas.critique import (
    AcceptRevisionRequest,
    CritiqueRecord,
    CritiqueSubmissionRequest,
    VideoRevision,
)
from app.services.repair_dispatcher import build_repair_prompt

logger = logging.getLogger(__name__)


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "apps").exists():
            return parent
    return current.parents[5] if len(current.parents) > 5 else Path.cwd()


REPO_ROOT = _find_repo_root()
CRITIQUES_LOG_PATH = REPO_ROOT / "apps/agents/sft_data_gen/critiques.jsonl"
ACCEPTED_TRAJECTORIES_PATH = REPO_ROOT / "apps/agents/sft_data_gen/accepted_trajectories.jsonl"


_critique_lock = Lock()
_in_memory_records: dict[str, CritiqueRecord] = {}
_revisions_store: dict[str, list[VideoRevision]] = {}


class CritiqueRecorder:
    """Manages the persistence of human critique and repair trajectories."""

    @staticmethod
    def ensure_log_dirs() -> None:
        try:
            CRITIQUES_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            ACCEPTED_TRAJECTORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create critique log directories: %s", exc)

    @classmethod
    def record_critique(cls, request: CritiqueSubmissionRequest) -> CritiqueRecord:
        cls.ensure_log_dirs()
        critique_id = f"critique_{uuid4().hex[:12]}"
        repair_prompt = build_repair_prompt(request)

        record = CritiqueRecord(
            critique_id=critique_id,
            video_generation_id=request.video_generation_id,
            revision=request.revision,
            category=request.category,
            feedback=request.feedback,
            timestamp_seconds=request.timestamp_seconds,
            target_object=request.target_object,
            severity=request.severity,
            session_id=request.session_id,
            created_at=datetime.now(timezone.utc),
            spatial_correction=request.spatial_correction,
            repair_prompt=repair_prompt,
            status="pending",
        )

        with _critique_lock:
            _in_memory_records[critique_id] = record

            # Update revision tags
            v_id = request.video_generation_id
            if v_id in _revisions_store:
                for rev in _revisions_store[v_id]:
                    if rev.revision == request.revision:
                        tag = f"❌ {request.category.value.replace('_', ' ').title()}"
                        if tag not in rev.critique_tags:
                            rev.critique_tags.append(tag)

            # Append to JSONL dataset
            try:
                with open(CRITIQUES_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record.model_dump(mode="json")) + "\n")
            except Exception as exc:
                logger.error("Failed to append critique to %s: %s", CRITIQUES_LOG_PATH, exc)

        logger.info(
            "Logged critique %s for video %s rev %d [%s]",
            critique_id,
            request.video_generation_id,
            request.revision,
            request.category.value,
        )
        return record

    @classmethod
    def register_revision(
        cls,
        video_generation_id: str,
        revision: int,
        stream_url: str,
        prompt: str | None = None,
        code: str | None = None,
    ) -> VideoRevision:
        rev = VideoRevision(
            revision=revision,
            video_generation_id=video_generation_id,
            stream_url=stream_url,
            prompt=prompt,
            code=code,
            critique_tags=[],
            accepted=False,
            created_at=datetime.now(timezone.utc),
        )

        with _critique_lock:
            revisions = _revisions_store.setdefault(video_generation_id, [])
            # Check if revision exists already
            for idx, existing in enumerate(revisions):
                if existing.revision == revision:
                    revisions[idx] = rev
                    return rev
            revisions.append(rev)

        return rev

    @classmethod
    def get_revisions(cls, video_generation_id: str) -> list[VideoRevision]:
        with _critique_lock:
            if video_generation_id in _revisions_store:
                return list(_revisions_store[video_generation_id])

            # Auto-seed v1 if not present
            v1 = VideoRevision(
                revision=1,
                video_generation_id=video_generation_id,
                stream_url=f"/api/videos/{video_generation_id}/stream",
                critique_tags=[],
                accepted=False,
                created_at=datetime.now(timezone.utc),
            )
            _revisions_store[video_generation_id] = [v1]
            return [v1]

    @classmethod
    def mark_accepted(cls, request: AcceptRevisionRequest) -> bool:
        cls.ensure_log_dirs()
        with _critique_lock:
            v_id = request.video_generation_id
            revisions = _revisions_store.get(v_id, [])
            accepted_rev = None

            for rev in revisions:
                if rev.revision == request.revision:
                    rev.accepted = True
                    tag = "✓ Verified Final"
                    if tag not in rev.critique_tags:
                        rev.critique_tags.append(tag)
                    accepted_rev = rev
                else:
                    rev.accepted = False

            # Log accepted trajectory for DPO/SFT training
            logged = False
            if accepted_rev:
                try:
                    payload = {
                        "video_generation_id": v_id,
                        "accepted_revision": request.revision,
                        "rating": request.rating,
                        "notes": request.notes,
                        "total_revisions": len(revisions),
                        "accepted_at": datetime.now(timezone.utc).isoformat(),
                        "final_code": accepted_rev.code,
                        "prompt": accepted_rev.prompt,
                    }
                    with open(ACCEPTED_TRAJECTORIES_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps(payload) + "\n")
                    logged = True
                except Exception as exc:
                    logger.error("Failed to log accepted trajectory: %s", exc)

        logger.info("Accepted revision %d for video %s", request.revision, request.video_generation_id)
        return logged
