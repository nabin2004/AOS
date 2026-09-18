param(
    [int]$Count = 500,
    [int]$Concurrency = 4
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   AOS Multi-Agent SFT Trace Generator (OmniRoute)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target traces: $Count" -ForegroundColor Cyan
Write-Host "Concurrency: $Concurrency" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Step 1] Generating $Count synthetic prompts..." -ForegroundColor Yellow
uv run python sft_data_gen/generate_prompts.py --num $Count --output sft_data_gen/prompts.jsonl --topics sft_data_gen/topics.txt
if ($LASTEXITCODE -ne 0) { throw "Prompt generation failed." }

Write-Host "`n[Step 2] Collecting multi-agent traces using OmniRoute endpoints..." -ForegroundColor Yellow
Write-Host "(Logfire remains enabled so that we can export traces for ALL agents in the graph)" -ForegroundColor DarkGray
# Note: We omit --fast so that AOS_LOGFIRE stays enabled! We want the full multi-agent traces to reach Logfire.
uv run python sft_data_gen/collect_traces.py --limit $Count --resume --concurrency $Concurrency
if ($LASTEXITCODE -ne 0) { throw "Trace collection failed." }

Write-Host "`n[Step 3] Exporting and formatting traces from Logfire into SFT format..." -ForegroundColor Yellow
uv run python export_graph_sft.py --days 1
if ($LASTEXITCODE -ne 0) { throw "Trace export failed." }

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " SUCCESS: Traces generated and formatted." -ForegroundColor Green
Write-Host " Your multi-turn dataset is ready in: export_traces/graph_sft/" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
