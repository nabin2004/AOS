from __future__ import annotations

import json

from ir.manim_ir import LectureIR
from pydantic import ValidationError

from tools.registry import aos_toolset


def validate_lecture_ir_data(lecture_ir_json: str) -> dict[str, object]:
    """Parse and validate a LectureIR document; return passed/issues."""
    try:
        LectureIR.model_validate_json(lecture_ir_json)
        return {"passed": True, "issues": []}
    except ValidationError as exc:
        issues = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        return {"passed": False, "issues": issues}


@aos_toolset.tool_plain
def validate_lecture_ir(lecture_ir_json: str) -> str:
    """Validate an AOS LectureIR JSON document against IR invariants.

    Returns JSON with keys ``passed`` (bool) and ``issues`` (list of strings).
    """
    return json.dumps(validate_lecture_ir_data(lecture_ir_json))
