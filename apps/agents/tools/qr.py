from __future__ import annotations

from urllib.parse import urlparse

import qrcode
from pydantic_ai import RunContext

from tools.registry import aos_toolset
from tools.deps import ToolDeps


def _validate_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"URL must be http(s): {url!r}")


@aos_toolset.tool
def generate_qr_code(
    ctx: RunContext[ToolDeps],
    url: str,
    filename: str = "repo_qr.png",
) -> str:
    """Generate a QR code PNG for a URL and return its absolute path."""
    _validate_url(url)
    out_path = ctx.deps.workspace_dir / filename
    img = qrcode.make(url.strip())
    img.save(out_path)
    return str(out_path.resolve())
