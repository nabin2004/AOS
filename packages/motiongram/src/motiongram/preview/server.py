"""Live preview HTTP server for YAML manifests."""

from __future__ import annotations

import contextlib
import json
import queue
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from motiongram.animate import smoothstep
from motiongram.core import Scene
from motiongram.export import PyAVEncoder
from motiongram.manifest.compose import ComposedProgram
from motiongram.manifest.errors import ManifestValidationError
from motiongram.manifest.loader import render_manifest
from motiongram.manifest.time import parse_time
from motiongram.render import SkiaRenderer

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_VIDEO_DEBOUNCE_S = 2.0
_WATCH_POLL_S = 0.3


def _write_png_bytes(rgba: Any) -> bytes:
    import numpy as np
    import skia

    arr = np.ascontiguousarray(rgba)
    img = skia.Image.fromarray(arr, skia.ColorType.kRGBA_8888_ColorType)
    data = img.encodeToData(skia.EncodedImageFormat.kPNG, 100)
    return bytes(data)


class PreviewState:
    """Thread-safe manifest preview state."""

    def __init__(
        self,
        manifest_path: Path,
        *,
        video_on_save: bool = False,
        initial_time: float = 0.0,
    ) -> None:
        self.manifest_path = manifest_path.expanduser().resolve()
        self.video_on_save = video_on_save
        self.scrub_time = initial_time
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[str | None]] = []

        self.program: ComposedProgram | None = None
        self.scene: Scene | None = None
        self.renderer: SkiaRenderer | None = None
        self.linear_timeline = False
        self.error: str | None = None
        self.updated_at: float = 0.0
        self.video_path = self.manifest_path.parent / ".motiongram" / "preview.mp4"
        self.video_ready = False
        self._video_encoding = False
        self._video_pending = False
        self._video_timer: threading.Timer | None = None
        self._encode_generation = 0

        self.reload()

    def subscribe(self) -> queue.Queue[str | None]:
        q: queue.Queue[str | None] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[str | None]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _broadcast(self, event: str) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            with contextlib.suppress(queue.Full):
                q.put_nowait(event)

    def reload(self) -> None:
        try:
            program, scene = render_manifest(self.manifest_path)
            renderer = SkiaRenderer(clear_color=program.clear_color)
            with self._lock:
                self.program = program
                self.scene = scene
                self.renderer = renderer
                self.linear_timeline = program.uses_custom_easing
                self.error = None
                self.updated_at = time.time()
            self._broadcast("reload")
            if self.video_on_save:
                self._schedule_video_encode()
        except ManifestValidationError as exc:
            with self._lock:
                self.error = str(exc)
                self.updated_at = time.time()
            self._broadcast("error")

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self.scene is None:
                return {
                    "ok": False,
                    "error": self.error or "No scene loaded",
                    "duration": 0.0,
                    "fps": 30.0,
                    "width": 0,
                    "height": 0,
                    "video_ready": False,
                    "updated_at": self.updated_at,
                }
            scene = self.scene
            return {
                "ok": self.error is None,
                "error": self.error,
                "duration": scene.duration,
                "fps": scene.fps,
                "width": scene.width,
                "height": scene.height,
                "video_ready": self.video_ready and self.video_path.is_file(),
                "updated_at": self.updated_at,
            }

    def render_frame_png(self, t: float) -> bytes | None:
        with self._lock:
            scene = self.scene
            renderer = self.renderer
            linear = self.linear_timeline
            err = self.error
        if scene is None or renderer is None or err is not None:
            return None
        t = max(0.0, min(scene.duration, t))
        ease = None if linear else smoothstep
        rgba = renderer.render_frame(scene, t, ease=ease)
        return _write_png_bytes(rgba)

    def _schedule_video_encode(self) -> None:
        with self._lock:
            if self._video_timer is not None:
                self._video_timer.cancel()
            self._video_pending = True
            timer = threading.Timer(_VIDEO_DEBOUNCE_S, self._start_video_encode)
            self._video_timer = timer
        timer.start()

    def _start_video_encode(self) -> None:
        with self._lock:
            if not self._video_pending or self._video_encoding:
                return
            if self.scene is None or self.error is not None:
                return
            self._video_pending = False
            self._video_encoding = True
            self._encode_generation += 1
            generation = self._encode_generation
            scene = self.scene
            renderer = self.renderer
            linear = self.linear_timeline
            output = self.video_path

        thread = threading.Thread(
            target=self._encode_video,
            args=(scene, renderer, linear, output, generation),
            daemon=True,
        )
        thread.start()

    def _encode_video(
        self,
        scene: Scene,
        renderer: SkiaRenderer | None,
        linear: bool,
        output: Path,
        generation: int,
    ) -> None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            enc = PyAVEncoder(
                scene=scene,
                output_path=output,
                renderer=renderer or SkiaRenderer(),
                linear_timeline=linear,
            )
            enc.encode(verbose=False)
            with self._lock:
                if generation == self._encode_generation:
                    self.video_ready = True
            self._broadcast("video_ready")
        except Exception:
            pass
        finally:
            with self._lock:
                if generation == self._encode_generation:
                    self._video_encoding = False


def _make_handler(state: PreviewState) -> type[BaseHTTPRequestHandler]:
    class PreviewHandler(BaseHTTPRequestHandler):
        server_version = "MotionGramPreview/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_bytes(
            self,
            data: bytes,
            *,
            status: HTTPStatus = HTTPStatus.OK,
            content_type: str,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            data = json.dumps(payload).encode("utf-8")
            self._send_bytes(data, status=status, content_type="application/json")

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/":
                html_path = _STATIC_DIR / "preview.html"
                data = html_path.read_bytes()
                self._send_bytes(data, content_type="text/html; charset=utf-8")
                return

            if path == "/status.json":
                self._send_json(state.status())
                return

            if path == "/frame.png":
                qs = parse_qs(parsed.query)
                t_raw = qs.get("t", ["0"])[0]
                try:
                    t = float(t_raw)
                except ValueError:
                    t = 0.0
                png = state.render_frame_png(t)
                if png is None:
                    self._send_json(
                        {"error": state.error or "No frame available"},
                        status=HTTPStatus.SERVICE_UNAVAILABLE,
                    )
                    return
                self._send_bytes(png, content_type="image/png")
                return

            if path == "/preview.mp4":
                if not state.video_path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = state.video_path.read_bytes()
                self._send_bytes(data, content_type="video/mp4")
                return

            if path == "/events":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                q = state.subscribe()
                try:
                    init = "event: reload\ndata: {}\n\n"
                    self.wfile.write(init.encode("utf-8"))
                    self.wfile.flush()
                    while True:
                        try:
                            event = q.get(timeout=15.0)
                        except queue.Empty:
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                            continue
                        if event is None:
                            break
                        msg = f"event: {event}\ndata: {{}}\n\n"
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    state.unsubscribe(q)
                return

            self.send_error(HTTPStatus.NOT_FOUND)

    return PreviewHandler


class PreviewServer:
    """HTTP preview server with optional file watching."""

    def __init__(
        self,
        manifest_path: Path | str,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        video_on_save: bool = False,
        initial_time: float = 0.0,
        watch: bool = True,
    ) -> None:
        self.manifest_path = Path(manifest_path).expanduser().resolve()
        self.host = host
        self.port = port
        self.watch = watch
        self.state = PreviewState(
            self.manifest_path,
            video_on_save=video_on_save,
            initial_time=initial_time,
        )
        handler = _make_handler(self.state)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._watch_stop = threading.Event()
        self._watch_thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start_watch(self) -> None:
        if not self.watch:
            return

        def _watch() -> None:
            last_mtime: float | None = None
            while not self._watch_stop.is_set():
                try:
                    mtime = self.manifest_path.stat().st_mtime
                    if last_mtime is not None and mtime != last_mtime:
                        self.state.reload()
                    last_mtime = mtime
                except OSError:
                    pass
                self._watch_stop.wait(_WATCH_POLL_S)

        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()

    def serve_forever(self) -> None:
        self.start_watch()
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        self._watch_stop.set()
        if self._watch_thread is not None:
            self._watch_thread.join(timeout=1.0)
        self._httpd.shutdown()
        self._httpd.server_close()


def run_preview_server(
    manifest_path: Path | str,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    video_on_save: bool = False,
    initial_time: str | float = 0.0,
    watch: bool = True,
) -> None:
    """Run the preview server until interrupted."""
    if isinstance(initial_time, str):
        t0 = parse_time(initial_time, field="time")
    else:
        t0 = float(initial_time)

    server = PreviewServer(
        manifest_path,
        host=host,
        port=port,
        video_on_save=video_on_save,
        initial_time=t0,
        watch=watch,
    )
    print(f"Preview server ready: {server.url}")
    print(f"Watching: {server.manifest_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping preview server.")
    finally:
        server.shutdown()
