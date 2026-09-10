import modal
import os
import subprocess
import tempfile
import boto3

audio_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install("pocket-tts>=0.1.0", "scipy>=1.14.0", "boto3>=1.34.0")
)

app = modal.App("aos-narrator-modal")

def upload_to_r2(audio_bytes: bytes, key: str) -> str:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["CLOUDFLARE_R2_KEY"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET"],
    )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        f.close()
        s3.upload_file(f.name, "aos-artifacts", key)
        os.unlink(f.name)
    return f"https://pub.r2.dev/aos-artifacts/{key}"

@app.function(image=audio_image, cpu=4, memory=2048, timeout=300,
              secrets=[modal.Secret.from_name("aos-secrets")])
def synthesize_beat(text: str, beat_id: str) -> dict:
    """Run Pocket TTS on a narration beat. Returns timestamps + R2 URL."""
    try:
        from narrator import Narrator
    except ImportError:
        from apps.audio_service.narrator import Narrator

    narrator = Narrator()
    result = narrator.synthesize(text)
    upload_to_r2(result.audio_bytes, f"audio/{beat_id}.wav")
    return {"url": f"https://pub.r2.dev/aos-artifacts/audio/{beat_id}.wav",
            "timestamps": result.word_timestamps}
