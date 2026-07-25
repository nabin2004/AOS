#!/usr/bin/env bash
# Install vLLM with the CPU backend into a dedicated venv (outside the AOS workspace).
#
# Standard `uv pip install vllm` pulls a GPU wheel and fails on CPU-only machines with:
#   RuntimeError: Failed to infer device type
#
# Usage:
#   ./apps/server/scripts/install-vllm-cpu.sh
#   VLLM_VENV=~/.venvs/aos-vllm VLLM_VERSION=0.26.0 ./apps/server/scripts/install-vllm-cpu.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VLLM_VENV="${VLLM_VENV:-${HOME}/.venvs/aos-vllm}"
VLLM_VERSION="${VLLM_VERSION:-0.26.0}"
PYTHON="${PYTHON:-3.12}"

WHEEL="https://github.com/vllm-project/vllm/releases/download/v${VLLM_VERSION}/vllm-${VLLM_VERSION}+cpu-cp38-abi3-manylinux_2_34_x86_64.whl"

echo "Creating venv at ${VLLM_VENV} (Python ${PYTHON})..."
uv venv "${VLLM_VENV}" --python "${PYTHON}"

# shellcheck source=/dev/null
source "${VLLM_VENV}/bin/activate"

echo "Removing any GPU vLLM build..."
uv pip uninstall vllm 2>/dev/null || true

echo "Installing vLLM ${VLLM_VERSION} CPU wheel..."
uv pip install "${WHEEL}" --torch-backend cpu

echo
echo "Aligning torch/torchvision/torchaudio to CPU builds..."
VLLM_VENV="${VLLM_VENV}" "${SCRIPT_DIR}/repair-vllm-cpu.sh"

echo
echo "Optional (recommended on Linux): preload tcmalloc for better CPU performance."
echo "  Arch:   sudo pacman -S gperftools"
echo "  Debian: sudo apt install libtcmalloc-minimal4"
echo "  export LD_PRELOAD=\$(find /usr -name 'libtcmalloc_minimal.so.4' 2>/dev/null | head -1):\${LD_PRELOAD:-}"
