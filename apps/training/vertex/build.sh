#!/usr/bin/env bash
set -euo pipefail

# Build and push SFT + GRPO training images to Artifact Registry.
#
# Usage (from repo root):
#   apps/training/vertex/build.sh --project MY_PROJECT --region us-central1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VERTEX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT=""
REGION="us-central1"
REPO="aos-training"
PUSH=1

usage() {
  cat <<'EOF'
Build and push AOS Vertex training containers.

Required:
  --project PROJECT_ID

Optional:
  --region REGION          (default: us-central1)
  --repo REPO_NAME         (default: aos-training)
  --no-push                Build locally only

Examples:
  apps/training/vertex/build.sh --project my-gcp-project
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --no-push)
      PUSH=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${PROJECT}" ]]; then
  echo "ERROR: --project is required" >&2
  usage
  exit 1
fi

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}"
SFT_IMAGE="${REGISTRY}/sft:latest"
GRPO_IMAGE="${REGISTRY}/grpo:latest"

echo "Ensuring Artifact Registry repo exists: ${REPO} (${REGION})"
gcloud artifacts repositories describe "${REPO}" \
  --project="${PROJECT}" \
  --location="${REGION}" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "${REPO}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --repository-format=docker \
    --description="AOS SFT/GRPO Vertex training images"

echo "Configuring docker auth for ${REGION}-docker.pkg.dev"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Building SFT image: ${SFT_IMAGE}"
docker build -f "${VERTEX_DIR}/Dockerfile.sft" -t "${SFT_IMAGE}" "${ROOT_DIR}"

echo "Building GRPO image: ${GRPO_IMAGE}"
docker build -f "${VERTEX_DIR}/Dockerfile.grpo" -t "${GRPO_IMAGE}" "${ROOT_DIR}"

if [[ "${PUSH}" -eq 1 ]]; then
  docker push "${SFT_IMAGE}"
  docker push "${GRPO_IMAGE}"
  echo "Pushed:"
  echo "  ${SFT_IMAGE}"
  echo "  ${GRPO_IMAGE}"
else
  echo "Built locally (not pushed):"
  echo "  ${SFT_IMAGE}"
  echo "  ${GRPO_IMAGE}"
fi
