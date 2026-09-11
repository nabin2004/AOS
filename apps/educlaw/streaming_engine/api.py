"""WebSocket Orchestrator for EduClaw asynchronous sequential chunked streaming.

Connects the background LLM producer to the Next.js UI via WebSockets, pushing
the MP4 video chunk paths the moment they finish rendering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.educlaw.streaming_engine.consumer import (
    render_branding_intro_video,
    render_single_slide,
)
from apps.educlaw.streaming_engine.models import SlideData
from apps.educlaw.streaming_engine.producer import (
    LectureProducer,
    generate_lecture_stream,
)

logger = logging.getLogger("educlaw.streaming_engine.api")

router = APIRouter()

# Global registry for backwards compatibility
active_queue: queue.Queue | None = None


@router.websocket("/ws/generate_lecture")
async def lecture_websocket_endpoint(websocket: WebSocket):
    """Main streaming orchestrator WebSocket endpoint."""
    await websocket.accept()
    global active_queue
    slide_queue: queue.Queue = queue.Queue()
    active_queue = slide_queue

    try:
        raw_msg = await websocket.receive_text()
        prompt = ""
        base_url = None
        api_key = None
        model = None
        total_slides = 3

        try:
            parsed = json.loads(raw_msg)
            if isinstance(parsed, dict):
                prompt = parsed.get("prompt") or parsed.get("text") or parsed.get("topic") or ""
                base_url = parsed.get("llm_base_url") or parsed.get("base_url")
                api_key = parsed.get("llm_api_key") or parsed.get("api_key")
                model = parsed.get("model") or parsed.get("model_id")
                if "total_slides" in parsed:
                    total_slides = int(parsed["total_slides"])
            else:
                prompt = str(parsed)
        except Exception:
            prompt = raw_msg

        prompt = prompt.strip()
        if not prompt:
            prompt = "Comprehensive lecture on the Lorenz attractor"

        # 1. Inform client and push branding intro immediately (16s buffer)
        await websocket.send_json({
            "type": "status",
            "message": f"Initializing lecture stream for: {prompt}",
        })

        try:
            intro_url = await asyncio.to_thread(render_branding_intro_video)
        except Exception as exc:
            logger.warning(f"Failed to render intro: {exc}")
            intro_url = "/media/streaming/intro.mp4"

        # Tell UI to play branding intro
        await websocket.send_json({
            "type": "play_intro",
            "url": intro_url,
        })

        # 2. Start LLM producer thread
        producer_thread = threading.Thread(
            target=generate_lecture_stream,
            args=(prompt, slide_queue),
            kwargs={
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
                "total_slides": total_slides,
            },
            daemon=True,
        )
        producer_thread.start()

        # 3. Stream loop: dequeue SlideData, render MP4 chunks, and push to Next.js
        while True:
            try:
                slide_data: SlideData = slide_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.5)
                continue

            # Push text / narration / code preview for chat UI
            await websocket.send_json({
                "type": "slide_generated",
                "slide_num": slide_data.slide_num,
                "narration": slide_data.narration,
                "code": slide_data.python_code,
                "is_final": slide_data.is_final,
            })

            # Notify rendering status
            await websocket.send_json({
                "type": "status",
                "message": f"Rendering Slide {slide_data.slide_num}...",
            })

            # Render chunk to MP4 in thread pool to prevent blocking event loop
            try:
                mp4_path = await asyncio.to_thread(render_single_slide, slide_data)
            except Exception as exc:
                logger.error(f"Error rendering slide {slide_data.slide_num}: {exc}")
                mp4_path = f"/media/streaming/slide_{slide_data.slide_num}.mp4"

            # Push chunk to Next.js player
            await websocket.send_json({
                "type": "video_chunk",
                "slide_num": slide_data.slide_num,
                "url": mp4_path,
                "is_final": slide_data.is_final,
            })

            if slide_data.is_final:
                await websocket.send_json({
                    "type": "complete",
                    "message": "Lecture generation and rendering complete.",
                })
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/generate_lecture")
    except Exception as exc:
        logger.error(f"Error in streaming websocket: {exc}")


def create_standalone_app() -> FastAPI:
    """Creates a standalone FastAPI app instance for testing or running the streaming engine alone."""
    app = FastAPI(title="EduClaw Streaming Engine API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount /media static directory
    curr = Path(__file__).resolve()
    repo_root = None
    for parent in [curr, *curr.parents]:
        if (parent / "pyproject.toml").is_file() and (parent / "apps").is_dir():
            repo_root = parent
            break
    root = repo_root or Path.cwd()
    media_dir = (root / "media").resolve()
    media_dir.mkdir(parents=True, exist_ok=True)
    streaming_dir = media_dir / "streaming"
    streaming_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")
    app.include_router(router)
    return app


app = create_standalone_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
