#!/usr/bin/env bash
set -euo pipefail

# Vertex AI entrypoint for Phase 1 SFT training.
# Downloads staged data from GCS, then runs apps/sft/run.py.

DATA_URI="${AOS_DATA_URI:-}"
DATA_PATH="${AOS_DATA_PATH:-/tmp/data/trajectories.jsonl}"
OUTPUT_DIR="${AIP_MODEL_DIR:-/tmp/output/sft}"
REPORT_TO="${AOS_REPORT_TO:-}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-uri)
      DATA_URI="$2"
      shift 2
      ;;
    --data-path)
      DATA_PATH="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --report-to)
      REPORT_TO="$2"
      shift 2
      ;;
    --smoke)
      EXTRA_ARGS+=(--epochs 1 --batch-size 1)
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "${REPORT_TO}" ]]; then
  if [[ -n "${WANDB_API_KEY:-}" ]]; then
    REPORT_TO="wandb"
  else
    REPORT_TO="tensorboard"
  fi
fi

if [[ -n "${DATA_URI}" ]]; then
  mkdir -p "$(dirname "${DATA_PATH}")"
  python /opt/aos/apps/training/vertex/gcs_download.py file "${DATA_URI}" "${DATA_PATH}"
fi

if [[ ! -f "${DATA_PATH}" ]]; then
  echo "ERROR: training data not found at ${DATA_PATH}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

cd /opt/aos/apps/sft
exec python run.py \
  --data-path "${DATA_PATH}" \
  --output-dir "${OUTPUT_DIR}" \
  --report-to "${REPORT_TO}" \
  "${EXTRA_ARGS[@]}"
