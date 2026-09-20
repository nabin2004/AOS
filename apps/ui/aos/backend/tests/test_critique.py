"""Unit tests for the Human-in-the-Loop Animation Critique & Review System."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.critique import (
    AcceptRevisionRequest,
    CritiqueCategory,
    CritiqueSubmissionRequest,
    SeverityLevel,
)
from app.services.critique_recorder import CritiqueRecorder
from app.services.repair_dispatcher import build_repair_prompt

client = TestClient(app)


def test_build_repair_prompt_positioning():
    req = CritiqueSubmissionRequest(
        video_generation_id="test_vid_001",
        revision=1,
        category=CritiqueCategory.POSITIONING,
        feedback="Labels are overlapping the formula",
        timestamp_seconds=12.5,
        target_object="formula_label",
        severity=SeverityLevel.HIGH,
    )
    prompt = build_repair_prompt(req)
    assert "POSITIONING" in prompt
    assert "12.5s" in prompt
    assert "formula_label" in prompt
    assert "Labels are overlapping the formula" in prompt
    assert "buffer margin" in prompt


def test_build_repair_prompt_visual_drift():
    req = CritiqueSubmissionRequest(
        video_generation_id="test_vid_002",
        revision=2,
        category=CritiqueCategory.VISUAL_DRIFT,
        feedback="Camera drifts away from the attractor trajectory",
        timestamp_seconds=20.0,
    )
    prompt = build_repair_prompt(req)
    assert "VISUAL_DRIFT" in prompt
    assert "20.0s" in prompt
    assert "camera angle" in prompt


def test_critique_recorder_lifecycle():
    vid_id = "test_lifecycle_vid_99"

    # Register v1 and v2
    CritiqueRecorder.register_revision(
        video_generation_id=vid_id,
        revision=1,
        stream_url=f"/api/videos/{vid_id}/stream",
        prompt="Explain Euler's identity",
        code="class Scene(Scene): ...",
    )

    CritiqueRecorder.register_revision(
        video_generation_id=vid_id,
        revision=2,
        stream_url=f"/api/videos/{vid_id}_v2/stream",
        prompt="Explain Euler's identity",
        code="class Scene(Scene): ... # fixed",
    )

    # Record critique on v1
    req = CritiqueSubmissionRequest(
        video_generation_id=vid_id,
        revision=1,
        category=CritiqueCategory.POSITIONING,
        feedback="Positioning is off",
    )
    record = CritiqueRecorder.record_critique(req)
    assert record.critique_id.startswith("critique_")

    # Check revisions
    revs = CritiqueRecorder.get_revisions(vid_id)
    assert len(revs) == 2
    v1 = next(r for r in revs if r.revision == 1)
    assert any("Positioning" in tag for tag in v1.critique_tags)

    # Accept v2
    accept_req = AcceptRevisionRequest(
        video_generation_id=vid_id,
        revision=2,
        rating=5,
        notes="Looks perfect!",
    )
    CritiqueRecorder.mark_accepted(accept_req)

    revs_after = CritiqueRecorder.get_revisions(vid_id)
    v2 = next(r for r in revs_after if r.revision == 2)
    assert v2.accepted is True
    assert any("Verified" in tag for tag in v2.critique_tags)


def test_critique_api_endpoints():
    vid_id = "api_test_vid_123"

    # 1. Get revisions (seeds v1)
    res = client.get(f"/api/v1/videos/{vid_id}/revisions")
    assert res.status_code == 200
    data = res.json()
    assert data["video_generation_id"] == vid_id
    assert len(data["revisions"]) >= 1

    # 2. Submit critique
    critique_payload = {
        "video_generation_id": vid_id,
        "revision": 1,
        "category": "visibility",
        "feedback": "The text size is too small to read on mobile devices",
        "timestamp_seconds": 5.4,
        "severity": "medium",
    }
    critique_res = client.post(f"/api/v1/videos/{vid_id}/critique", json=critique_payload)
    assert critique_res.status_code == 200
    critique_data = critique_res.json()
    assert critique_data["success"] is True
    assert critique_data["category"] == "visibility"
    assert "Repairing visibility" in critique_data["suggested_action"]

    # 3. Accept revision
    accept_payload = {
        "video_generation_id": vid_id,
        "revision": 1,
        "rating": 5,
    }
    accept_res = client.post(f"/api/v1/videos/{vid_id}/accept", json=accept_payload)
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert accept_data["success"] is True
