"""TRL compatibility shims and workarounds for SFTTrainer."""

from __future__ import annotations

import functools
import types
from typing import Any

import trl.trainer.sft_trainer as _sft_module
from trl import SFTConfig

# Fix TRL issue #6483: SFTTrainer's _patch_chunked_ce_lm_head assumes original_forward has .__func__,
# which crashes with AttributeError when model.forward is a functools.partial (e.g. from
# accelerate device_map or bitsandbytes prepare_model_for_kbit_training).
if hasattr(_sft_module, "_patch_chunked_ce_lm_head"):
    _orig_patch_chunked_ce_lm_head = _sft_module._patch_chunked_ce_lm_head

    def _safe_patch_chunked_ce_lm_head(target, *args, **kwargs):
        fwd = getattr(target, "forward", None)
        if isinstance(fwd, functools.partial) and not hasattr(fwd, "__func__"):
            inner = fwd.func
            while isinstance(inner, functools.partial):
                inner = inner.func
            try:
                fwd.__func__ = getattr(inner, "__func__", inner)
            except Exception:
                pass
        try:
            return _orig_patch_chunked_ce_lm_head(target, *args, **kwargs)
        except Exception as exc:
            print(f"trainer: bypassed _patch_chunked_ce_lm_head ({exc}); falling back to standard forward.")
            return None

    _sft_module._patch_chunked_ce_lm_head = _safe_patch_chunked_ce_lm_head


def get_safe_sft_config_kwargs() -> dict[str, Any]:
    """Return extra kwargs for SFTConfig to disable problematic experimental patches."""
    kwargs: dict[str, Any] = {}
    if hasattr(SFTConfig, "loss_type"):
        kwargs["loss_type"] = "nll"
    return kwargs
