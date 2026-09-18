param(
    [string]$ImageName = "nabinoli2004/qwen-manimator-vllm",
    [string]$Tag = "latest",
    [string]$BaseModel = "Qwen/Qwen2.5-7B-Instruct"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Building vLLM Docker Image with baked-in LoRA" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Base Model: $BaseModel" -ForegroundColor Cyan
Write-Host "LoRA Repo: nabin2004/qwen-Manimator-1-sft" -ForegroundColor Cyan
Write-Host "Docker Image: ${ImageName}:${Tag}" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Step 1] Building Docker Image (This will download the 15GB+ model)..." -ForegroundColor Yellow
docker build -f Dockerfile.runpod -t "${ImageName}:${Tag}" --build-arg BASE_MODEL=$BaseModel .
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Docker build failed. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}

Write-Host "`n[Step 2] Pushing Image to Docker Hub..." -ForegroundColor Yellow
docker push "${ImageName}:${Tag}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Docker push failed. Are you logged in? (Run: docker login)" -ForegroundColor Red
    exit 1
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " SUCCESS: Docker Image built and pushed!" -ForegroundColor Green
Write-Host " You can now deploy this image on RunPod Serverless." -ForegroundColor Green
Write-Host " Ensure you expose port 8000 when configuring the endpoint." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
