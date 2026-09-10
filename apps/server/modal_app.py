"""Production Modal serverless orchestration app for AOS."""
from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from typing import Any
import requests

import modal
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, make_asgi_app

REQUEST_COUNT = Counter("aos_requests_total", "Total API requests", ["endpoint", "status"])
RENDER_DURATION = Histogram("aos_render_duration_seconds", "Manim render duration")
PIPELINE_STEPS = Counter("aos_pipeline_steps_total", "Pipeline step completions", ["step"])


# 1. Base Container Image with System Dependencies & LaTeX
manim_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "ffmpeg",
        "libcairo2-dev",
        "libpango1.0-dev",
        "texlive",
        "texlive-latex-extra",
        "texlive-fonts-extra",
        "git",
    )
    .pip_install(
        "manim>=0.18.0",
        "boto3>=1.34.0",
        "pydantic-ai>=0.0.14",
        "fastapi>=0.110.0",
        "uvicorn>=0.28.0",
        "prometheus-client>=0.20.0",
        "logfire[fastapi]>=0.50.0",
        "manim-voiceover>=0.1.1",
        "requests",
        "pocket-tts>=0.1.0",
        "scipy>=1.14.0"
    )
)

app = modal.App("aos-api", image=manim_image)

job_store = modal.Dict.from_name("aos-job-store", create_if_missing=True)

# SECURE: No secrets mounted to prevent exfiltration by untrusted AI code.
@app.function(
    image=manim_image,
    cpu=4.0,
    memory=4096,
    timeout=600,
)
def render_scene_modal(scene_code: str, scene_name: str, presigned_put_url: str, quality: str = "l") -> str:
    """Renders a single Manim scene and uploads MP4 via Presigned URL."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(scene_code)
        scene_file = f.name

    out_dir = tempfile.mkdtemp()
    cmd = [
        "manim",
        f"-q{quality}",
        scene_file,
        scene_name,
        "--media_dir",
        out_dir,
        "--output_file",
        f"{scene_name}.mp4",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Manim render error: {res.stderr}")

    mp4_path = os.path.join(out_dir, "videos", f"{scene_name}.mp4")
    if not os.path.exists(mp4_path):
        for root, _, files in os.walk(out_dir):
            for file in files:
                if file.endswith(".mp4"):
                    mp4_path = os.path.join(root, file)
                    break

    with open(mp4_path, "rb") as f:
        resp = requests.put(presigned_put_url, data=f, headers={"Content-Type": "video/mp4"})
        resp.raise_for_status()

    return scene_name


# 3. Audio Narration Worker Function
@app.function(
    image=manim_image,
    cpu=2.0,
    memory=2048,
    timeout=300,
    secrets=[modal.Secret.from_name("aos-secrets")],
)
def synthesize_beat_audio(text: str, beat_id: str) -> dict[str, Any]:
    """Synthesizes beat audio via Kyutai Pocket TTS and stores in R2."""
    import boto3
    from botocore.config import Config

    try:
        from apps.audio_service.narrator import Narrator
        narrator = Narrator()
        result = narrator.synthesize(text)

        audio_filename = f"{beat_id}.wav"
        audio_path = os.path.join(tempfile.gettempdir(), audio_filename)
        with open(audio_path, "wb") as f:
            f.write(result.audio_bytes)
    except Exception as e:
        # Fallback for testing environments without full weights downloaded
        audio_filename = f"{beat_id}.wav"
        audio_path = os.path.join(tempfile.gettempdir(), audio_filename)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", audio_path], check=True)

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["CLOUDFLARE_R2_KEY"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    object_key = f"audio/{beat_id}.wav"
    s3.upload_file(audio_path, os.environ["CLOUDFLARE_R2_BUCKET"], object_key, ExtraArgs={"ContentType": "audio/wav"})
    public_url = f"{os.environ['CLOUDFLARE_R2_PUBLIC_URL'].rstrip('/')}/{object_key}"
    return {"beat_id": beat_id, "audio_url": public_url}


# 4. FastAPI ASGI Server Definition
web_app = FastAPI(title="AOS Orchestration API", version="2.0.0")

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
web_app.mount("/metrics", metrics_app)

class GenerateRequest(BaseModel):
    prompt: str
    fast: bool = False
    cinematic: bool = False

@web_app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "AOS Serverless API", "version": "2.0.0"}

def _run_agentic_pipeline(job_id: str, prompt: str, cinematic: bool, fast: bool):
    try:
        from apps.agents.runner import run_aos_pipeline
        job_store[job_id] = {"status": "running", "prompt": prompt, "cinematic": cinematic}
        run_aos_pipeline(prompt, fast=fast, cinematic=cinematic)
        job_store[job_id] = {"status": "completed", "prompt": prompt, "cinematic": cinematic}
    except Exception as e:
        job_store[job_id] = {"status": "failed", "prompt": prompt, "cinematic": cinematic, "error": str(e)}

@web_app.post("/api/v1/generate")
def start_generation(req: GenerateRequest, bg: BackgroundTasks) -> dict[str, str]:
    REQUEST_COUNT.labels(endpoint="/api/v1/generate", status="ok").inc()
    job_id = uuid.uuid4().hex
    job_store[job_id] = {"status": "queued", "prompt": req.prompt, "cinematic": req.cinematic}
    bg.add_task(_run_agentic_pipeline, job_id, req.prompt, req.cinematic, req.fast)
    return {"job_id": job_id, "status": "queued"}

@web_app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]

@app.function(
    image=manim_image,
    cpu=2.0,
    memory=2048,
    timeout=600,
    secrets=[modal.Secret.from_name("aos-secrets")],
)
@modal.asgi_app()
def fastapi_app():
    return web_app
