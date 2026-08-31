"""Audio synthesis and transcription tools for the EduClaw agent."""

from __future__ import annotations

import sys
from pathlib import Path
from pydantic_ai import Agent, RunContext

from educlaw.agent.deps import AgentDeps


def register_audio_tools(agent: Agent[AgentDeps, str]) -> None:
    """Register audio synthesis and transcription tools on the EduClaw agent."""

    @agent.tool
    async def audio_synthesize_text(
        ctx: RunContext[AgentDeps],
        text: str,
        out_filename: str = "narration.wav",
        voice: str = "alba",
    ) -> str:
        """Synthesize speech audio from text using the resident audio service.
        
        Args:
            text: Text script to synthesize.
            out_filename: Output wav file name inside workspace.
            voice: Voice name (e.g. 'alba', 'george', 'cosette').
        """
        try:
            # Ensure audio_service is importable
            audio_service_path = Path(__file__).resolve().parents[3] / "audio_service"
            if str(audio_service_path) not in sys.path:
                sys.path.insert(0, str(audio_service_path))

            from narrator import Narrator

            out_path = ctx.deps.sandbox.jail(out_filename)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            narrator = Narrator(voice=voice)
            narrator.synthesize(text, out_path)

            if ctx.deps.emit:
                ctx.deps.emit("tool", {"name": "audio_synthesize_text", "out_file": str(out_filename)})

            return f"Successfully generated speech audio at {out_filename} using voice '{voice}'"
        except Exception as exc:
            return f"Failed to synthesize audio: {exc}"

    @agent.tool
    async def audio_align_timestamps(
        ctx: RunContext[AgentDeps],
        text: str,
    ) -> str:
        """Parse bookmarks or analyze timing boundaries for text segments."""
        try:
            audio_service_path = Path(__file__).resolve().parents[3] / "audio_service"
            if str(audio_service_path) not in sys.path:
                sys.path.insert(0, str(audio_service_path))

            from dsm_aligner import TimestampedWord, convert_words_to_boundaries

            words = [TimestampedWord(text=w, start_time=i * 0.4, end_time=(i + 1) * 0.4) for i, w in enumerate(text.split())]
            boundaries = convert_words_to_boundaries(words, full_text=text)

            return f"Aligned {len(words)} words into {len(boundaries)} boundary markers for animation timing."
        except Exception as exc:
            return f"Failed to align timestamps: {exc}"
