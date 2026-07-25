#!/usr/bin/env bash
# Reinstall CPU-matched torch/torchvision/torchaudio in an existing aos-vllm venv.
#
# Fixes: RuntimeError: operator torchvision::nms does not exist
# (CPU torch + CUDA/generic torchvision mismatch after vLLM CPU wheel install)
#
# Usage:
#   ./apps/server/scripts/repair-vllm-cpu.sh
#   VLLM_VENV=~/.venvs/aos-vllm ./apps/server/scripts/repair-vllm-cpu.sh

set -euo pipefail

VLLM_VENV="${VLLM_VENV:-${HOME}/.venvs/aos-vllm}"
# Pinned to match vLLM 0.26.0; bump with VLLM_VERSION when upgrading vLLM.
TORCH_VERSION="${TORCH_VERSION:-2.11.0}"
TORCHVISION_VERSION="${TORCHVISION_VERSION:-0.26.0}"
TORCHAUDIO_VERSION="${TORCHAUDIO_VERSION:-2.11.0}"

if [[ ! -f "${VLLM_VENV}/bin/activate" ]]; then
  echo "venv not found at ${VLLM_VENV}. Run: ./apps/server/scripts/install-vllm-cpu.sh" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${VLLM_VENV}/bin/activate"

echo "Reinstalling CPU torch stack in ${VLLM_VENV}..."
echo "  torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} torchaudio==${TORCHAUDIO_VERSION}"
echo

uv pip uninstall torchvision torchaudio 2>/dev/null || true
uv pip install \
  "torch==${TORCH_VERSION}" \
  "torchvision==${TORCHVISION_VERSION}" \
  "torchaudio==${TORCHAUDIO_VERSION}" \
  --torch-backend cpu \
  --reinstall

echo
echo "Verifying imports..."
python - <<'PY'
import torch
import torchvision
import vllm
from vllm.platforms import current_platform

for name, mod in [("torch", torch), ("torchvision", torchvision)]:
    ver = mod.__version__
    if "+cpu" not in ver:
        raise SystemExit(
            f"{name} {ver} is not a +cpu build. "
            "Re-run ./apps/server/scripts/repair-vllm-cpu.sh"
        )
    print(f"  {name}: {ver}")

platform_name = type(current_platform).__name__
print(f"  vllm: {vllm.__version__} ({platform_name})")
if "Cpu" not in platform_name and "CPU" not in platform_name:
    raise SystemExit("Expected CpuPlatform — install the vLLM CPU wheel first.")

print("OK — CPU torch stack and vLLM imports verified.")
PY

echo
echo "Next: source ${VLLM_VENV}/bin/activate && ./apps/server/scripts/serve-cpu.sh"
