"""DBOSAgent wrappers for the Manim pipeline agents.

Import after `dbos_setup` configures DBOS; call `ensure_dbos_launched()`
before running these when `AOS_DBOS=1`.
"""

from __future__ import annotations

import dbos_setup  # noqa: F401 — configure DBOS before wrapping
from pydantic_ai.durable_exec.dbos import DBOSAgent

from classifier_agent import classifier_agent
from coder_agent import coder_agent
from lecture_planner import lecture_planner_agent
from teaching_script import teaching_script_agent

durable_classifier = DBOSAgent(classifier_agent)
durable_lecture_planner = DBOSAgent(lecture_planner_agent)
durable_teaching_script = DBOSAgent(teaching_script_agent)
durable_coder = DBOSAgent(coder_agent)

durable_classifier = DBOSAgent(classifier_agent)
durable_lecture_planner = DBOSAgent(lecture_planner_agent)
durable_coder = DBOSAgent(coder_agent)
