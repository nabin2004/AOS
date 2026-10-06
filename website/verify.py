"""Small offline check for the static GitHub Pages artifact."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent


class PageAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local_assets: list[str] = []
        self.videos: list[dict[str, object]] = []
        self._current_video: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "video":
            self._current_video = {"controls": "controls" in values, "muted": "muted" in values, "source": None}
            self.videos.append(self._current_video)
        elif tag == "source" and self._current_video is not None:
            self._current_video["source"] = values.get("src")
        for name in ("src", "href"):
            value = values.get(name)
            if value and not value.startswith(("https://", "http://", "#", "mailto:")):
                self.local_assets.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "video":
            self._current_video = None


page = ROOT / "index.html"
parser = PageAssets()
parser.feed(page.read_text(encoding="utf-8"))
errors: list[str] = []

if len(parser.videos) != 4:
    errors.append(f"expected 4 generated videos, found {len(parser.videos)}")
for index, video in enumerate(parser.videos, start=1):
    if not video["controls"]:
        errors.append(f"video {index} is missing playback controls")
    if video["muted"]:
        errors.append(f"video {index} is muted")
    source = video["source"]
    if not isinstance(source, str) or not source.endswith(".mp4"):
        errors.append(f"video {index} is missing an MP4 source")
for asset in parser.local_assets:
    parsed = urlparse(asset)
    target = ROOT / parsed.path
    if not target.is_file():
        errors.append(f"missing local asset: {asset}")
if "id=\"projects\"" in page.read_text(encoding="utf-8").lower():
    errors.append("page unexpectedly contains a Projects section")

if errors:
    raise SystemExit("\n".join(errors))
print(f"Pages artifact OK: {len(parser.videos)} unmuted, controllable videos; all local links resolve.")
