"""Core turn loop: steer → compact → model → memory."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from educlaw.agent.compaction import over_threshold, run_full_compaction, run_micro_compaction
from educlaw.agent.context import ContextWindow, estimate_messages_tokens
from educlaw.agent.deps import AgentDeps
from educlaw.agent.steering import GateDecision, apply_gate
from educlaw.memory.files import append_memory_digest, load_agents_md
from educlaw.memory.store import IngestUnavailable
from educlaw.settings import Settings
from dotenv import load_dotenv

load_dotenv()  


class AgentTurnHandler:
    """Orchestrates user input, steering, compaction, the model, and memory."""

    def __init__(
        self,
        agent: Agent[AgentDeps, str],
        deps: AgentDeps,
        session_id: str | None = None,
        turn_id: str | None = None,
        message_history: list[ModelMessage] | None = None,
        compaction_model: str | None = None,
        session_log: list[dict[str, Any]] | None = None,
        settings: Settings | None = None,
        summarizer: Callable[[str], Any] | None = None,
    ) -> None:
        self.agent = agent
        self.deps = deps
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.turn_id = turn_id or "0"
        self.message_history: list[ModelMessage] = list(message_history or [])
        self.compaction_model = compaction_model
        self.session_log = session_log if session_log is not None else []
        self.settings = settings or Settings.from_env()
        self.summarizer = summarizer
        self.context_window = ContextWindow.resolve(
            explicit=self.settings.context_window_tokens,
            model_id=self.settings.model,
        )
        self._last_usage_total: int | None = None
        self._turns_since_digest = 0
        self.running = False
        self.aborted = False

    def clear(self) -> None:
        self.message_history = []
        self._last_usage_total = None
        self._turns_since_digest = 0

    async def get_context_size(self) -> int:
        return estimate_messages_tokens(self.message_history, self._last_usage_total)

    async def ask_human(self, question: str = "") -> str:
        if self.deps.emit:
            self.deps.emit("ask_human", {"question": question})
        return ""

    async def micro_compaction(self) -> None:
        self.message_history = await run_micro_compaction(self.message_history)

    async def full_compaction(self) -> None:
        summarizer = self.summarizer
        if summarizer is None and self.compaction_model:

            async def _model_summarize(text: str) -> str:
                result = await self.agent.run(
                    f"Summarize this conversation for future context. Keep facts, goals, and open work.\n\n{text}",
                    model=self.compaction_model,
                    deps=self.deps,
                )
                return str(result.output)

            summarizer = _model_summarize
        self.message_history = await run_full_compaction(
            self.message_history,
            tail_count=self.settings.compaction_tail,
            summarizer=summarizer,
        )

    async def maybe_compact(self) -> None:
        if over_threshold(
            self.message_history,
            self.context_window.tokens,
            self.settings.compaction_threshold,
            self._last_usage_total,
        ):
            await self.micro_compaction()
            if over_threshold(
                self.message_history,
                self.context_window.tokens,
                self.settings.compaction_threshold,
                None,
            ):
                await self.full_compaction()

    async def _build_instructions(self, user_text: str) -> str:
        agents_md = load_agents_md(self.deps.cwd)
        strategy = await self.deps.memory.strategy()
        retrieved = await self.deps.memory.retrieve(user_text)
        parts = [
            "You are running inside the EduClaw harness.",
        ]
        if agents_md.strip():
            parts.append("## AGENTS.md\n" + agents_md.strip())
        if strategy:
            parts.append("## Memory strategy\n" + str(strategy).strip())
        if retrieved:
            parts.append("## Retrieved memory\n" + str(retrieved).strip())
        return "\n\n".join(parts)

    def _compose_prompt(self, user_text: str, steer_texts: list[str]) -> str:
        if not steer_texts:
            return user_text
        steering = "\n".join(f"- {item}" for item in steer_texts)
        return f"{user_text}\n\n[Steering — apply before continuing]\n{steering}"

    async def run_turn(self, user_text: str) -> str:
        self.running = True
        self.aborted = False
        try:
            decision, steer_texts, aborted = apply_gate(self.deps.steering, running=True)
            if aborted or decision is GateDecision.ABORT:
                self.aborted = True
                self.session_log.append({"event": "abort", "session_id": self.session_id})
                if self.deps.emit:
                    self.deps.emit("abort", {})
                return "(turn aborted by steering gate)"

            await self.maybe_compact()
            prompt = self._compose_prompt(user_text, steer_texts)
            instructions = await self._build_instructions(user_text)

            result = await self.agent.run(
                prompt,
                message_history=self.message_history,
                deps=self.deps,
                instructions=instructions,
            )
            self.message_history = list(result.all_messages())
            output = str(result.output)
            usage = getattr(result, "usage", None)
            if callable(usage):
                usage = usage()
            total = getattr(usage, "total_tokens", None)
            if isinstance(total, int):
                self._last_usage_total = total

            await self._ingest_turn(user_text, output)
            self.session_log.append(
                {
                    "event": "turn",
                    "session_id": self.session_id,
                    "user": user_text,
                    "assistant": output,
                }
            )
            if self.deps.emit:
                self.deps.emit("turn", {"user": user_text, "assistant": output})
            return output
        finally:
            self.running = False

    async def _ingest_turn(self, user_text: str, assistant_text: str) -> None:
        conversation = [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
        try:
            await self.deps.memory.ingest(conversation, source=self.session_id)
        except IngestUnavailable:
            if self.deps.emit:
                self.deps.emit("memory_skip", {"reason": "ingest_unavailable"})
        self._turns_since_digest += 1
        if self._turns_since_digest >= self.settings.memory_digest_every:
            digest = assistant_text.strip().replace("\n", " ")
            if len(digest) > 240:
                digest = digest[:240] + "…"
            append_memory_digest(self.deps.cwd, digest)
            self._turns_since_digest = 0
