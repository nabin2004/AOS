"""EduClaw Audio Test Suite & Harness.

Evaluates audio capabilities (Pocket TTS, Kyutai DSM STT/TTS, and timestamp alignment)
directly on the local machine / laptop environment.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def test_pocket_tts(output_dir: Path) -> dict:
    """Test standard resident Pocket TTS (CPU)."""
    console.print("[bold cyan]1. Testing Pocket TTS (Resident CPU model)...[/bold cyan]")
    try:
        # Import from audio_service
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "audio_service"))
        from narrator import Narrator

        start_load = time.time()
        narrator = Narrator()
        load_time = time.time() - start_load
        console.print(f"  [green][OK][/green] Pocket TTS loaded in {load_time:.2f}s (Sample rate: {narrator.sample_rate} Hz)")

        test_text = "Welcome to EduClaw. Today we are testing the audio synthesis engine on this laptop."
        out_file = output_dir / "pocket_tts_test.wav"

        start_synth = time.time()
        narrator.synthesize(test_text, out_file)
        synth_time = time.time() - start_synth

        # Calculate audio duration
        import scipy.io.wavfile

        rate, data = scipy.io.wavfile.read(out_file)
        duration = len(data) / rate
        rtf = duration / synth_time if synth_time > 0 else 0

        console.print(f"  [green][OK][/green] Synthesized {duration:.2f}s audio in {synth_time:.2f}s (RTF: {rtf:.1f}x real-time)")
        console.print(f"  [green][OK][/green] Saved wav to: {out_file}")

        return {
            "status": "PASS",
            "backend": "Pocket TTS (CPU)",
            "load_time_sec": round(load_time, 2),
            "synth_time_sec": round(synth_time, 2),
            "audio_duration_sec": round(duration, 2),
            "rtf": round(rtf, 1),
            "out_file": str(out_file),
        }
    except Exception as e:
        console.print(f"  [red][ERROR] Pocket TTS test failed:[/red] {e}")
        return {"status": "FAIL", "backend": "Pocket TTS (CPU)", "error": str(e)}


def test_dsm_aligner() -> dict:
    """Test DSM word boundary converter with sample timestamped tokens."""
    console.print("\n[bold cyan]2. Testing DSM Word Boundary Aligner for Manim...[/bold cyan]")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "audio_service"))
        from dsm_aligner import TimestampedWord, convert_words_to_boundaries

        sample_words = [
            TimestampedWord(text="Welcome", start_time=0.0, end_time=0.4),
            TimestampedWord(text="to", start_time=0.45, end_time=0.6),
            TimestampedWord(text="AOS", start_time=0.65, end_time=1.1),
            TimestampedWord(text="lectures", start_time=1.15, end_time=1.8),
        ]
        full_text = "Welcome to AOS lectures"
        boundaries = convert_words_to_boundaries(sample_words, full_text=full_text)

        console.print(f"  [green][OK][/green] Converted {len(sample_words)} words into {len(boundaries)} Manim boundaries.")
        for b in boundaries[1:]:
            console.print(f"    - Word: '{b['text']}', Text Offset: {b['text_offset']}, Audio Offset: {b['audio_offset']/10_000_000:.2f}s")

        return {
            "status": "PASS",
            "backend": "DSM Aligner",
            "word_count": len(sample_words),
            "boundary_count": len(boundaries),
        }
    except Exception as e:
        console.print(f"  [red][ERROR] DSM Aligner test failed:[/red] {e}")
        return {"status": "FAIL", "backend": "DSM Aligner", "error": str(e)}


def test_dsm_server_connection(server_url: str = "ws://127.0.0.1:8080") -> dict:
    """Check if Rust moshi-server is currently active on local port."""
    console.print(f"\n[bold cyan]3. Checking Rust moshi-server at {server_url}...[/bold cyan]")
    import socket

    host = "127.0.0.1"
    port = 8080
    if ":" in server_url.replace("ws://", ""):
        parts = server_url.replace("ws://", "").split(":")
        host = parts[0]
        port = int(parts[1])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    result = s.connect_ex((host, port))
    s.close()

    if result == 0:
        console.print(f"  [green][ONLINE][/green] Rust moshi-server is ONLINE on {host}:{port}!")
        return {"status": "ONLINE", "url": server_url}
    else:
        console.print(f"  [yellow][INFO][/yellow] Rust moshi-server is not running on {host}:{port}.")
        console.print("    (To start Rust server: `moshi-server worker --config configs/config-tts.toml`)")
        return {"status": "OFFLINE", "url": server_url}


def main():
    parser = argparse.ArgumentParser(description="EduClaw Audio Diagnostic & Eval Suite")
    parser.add_argument("--test", choices=["pocket", "dsm", "server", "all"], default="all")
    parser.add_argument("--out-dir", default="./eval_output", help="Directory to save test audio")
    parser.add_argument("--server-url", default="ws://127.0.0.1:8080")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel("[bold green]EduClaw Audio Evaluation & Harness Test[/bold green]\nTesting Pocket TTS & Kyutai Delayed Streams Modeling (DSM)"))

    results = []
    if args.test in ["pocket", "all"]:
        results.append(test_pocket_tts(out_dir))
    if args.test in ["dsm", "all"]:
        results.append(test_dsm_aligner())
    if args.test in ["server", "all"]:
        results.append(test_dsm_server_connection(args.server_url))

    # Summary table
    table = Table(title="Audio Evaluation Results")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    for r in results:
        backend = r.get("backend", r.get("url", "Test"))
        status = r.get("status", "UNKNOWN")
        style = "green" if status in ["PASS", "ONLINE"] else "yellow" if status == "OFFLINE" else "red"
        details = f"RTF: {r.get('rtf', 'N/A')}x, Dur: {r.get('audio_duration_sec', 'N/A')}s" if "rtf" in r else r.get("error", "OK")
        table.add_row(backend, f"[{style}]{status}[/{style}]", details)

    console.print("\n")
    console.print(table)


if __name__ == "__main__":
    main()
