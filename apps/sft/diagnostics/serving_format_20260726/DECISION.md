# Decision gate: Gemma E2B SFT serving-format diagnosis

Date: 2026-07-26
Artifacts: this directory (`raw_*.json`, `analysis_report.json`, `SUMMARY.md`, probes)

## Executive verdict

**Do not jump to Qwen2.5-Coder-14B yet.**

Gate classification: **data/contract bug (+ prompt-conditioned CodeMode), not chat-template mismatch, not quantization degeneration.**

The published GGUF’s Ollama chat template is **byte-identical** to [`apps/sft/templates/gemma4_training.jinja`](../../templates/gemma4_training.jinja) (21551 bytes). Under greedy decoding (`temperature=0`), the same model can emit **correct** CodeMode (`await manim_write(...)`) or **incorrect** top-level Manim depending on the system/user prompt — so the weights know the right format; the production prompt + contaminated SFT distribution push the wrong one.

Matched `apps/sft/infer.py` was **skipped** (no CUDA on this host). All generation probes used the production GGUF via Ollama, which is the hybrid coder path.

---

## Plan steps — results

### 1. Bypass PydanticAI — raw GGUF completions

| Probe | Result |
|---|---|
| `/api/chat` no tools, temp=0, 1024 tok | Markdown ```python with `from manim import *`. **No** `<\|tool_call>` markup. Truncated (`done_reason=length`). Thinking present (~803 chars). |
| `/v1/chat/completions` + `run_code` tool, **short** Infer-style system + short Euler prompt, temp=0 | `finish_reason=tool_calls`, `run_code` with **`wrap_then_manim_write`** — CodeMode preflight **PASS**. |
| Same API + **full** production `CODE_PROMPT` + full Euler user message, temp=0 | `finish_reason=tool_calls`, `run_code` with **`raw_manim_top_level`** — CodeMode preflight **FAIL** (`codemode_star_import`). Reproduces hybrid Euler failure. |
| Native `/api/chat` + tools, `num_predict=512` | HTTP 500: `invalid tool call arguments for "run_code": unexpected end of JSON input` (truncated mid-JSON). Secondary serving fragility. |

### 2. Syntax diff vs parsers / CodeMode

| Surface | Status |
|---|---|
| Jinja golden render | `<\|tool_call>call:run_code{code:<\|"\|>…await manim_write…<\|"\|>}<tool_call\|>` |
| Ollama OpenAI `tool_calls` | Structured JSON `{"code":"..."}` — what PydanticAI consumes. Wire parse works. |
| `parse_gemma_tool_calls` on no-tools prose | 0 calls (expected: no Gemma markup emitted). |
| CodeMode contract | Fail when `code` starts with `from manim import *`; pass when `await manim_write(code=...)`. |

**Refined vs original hypothesis:** Teacher→student markup gap is **not** the failure mode here. Training already targets Gemma tool markup; Ollama `peg-gemma4` converts it to OpenAI tools successfully. The mismatch is **semantic** (what goes inside `code`), not delimiter/grammar.

### 3. GGUF chat template == SFT template?

**Yes — identical.**

- `ollama show` `template` field == `gemma4_training.jinja` exactly.
- Distinctive markers (`<\|tool_call>call:`, `<\|"\|>`, `<\|channel>thought`, `{% generation %}`) present in both.
- Modelfile also shows a **simplified Go `TEMPLATE`** for basic chat (`{{ if .System }}…`) plus stop params: `<bos>`, `<\|turn>`, `<turn\|>`, `<\|turn>user`. Runtime tool chat uses the Jinja/`peg-gemma4` path (`chat format: peg-gemma4` in server log), not that Go stub alone.

Stop-token note: listing `<bos>` as a stop is unusual; did not prevent tool_calls finishes in greedy probes. Turn-2 amnesia after Monty retry remains a separate multi-turn / thinking-channel concern (see Euler hybrid msg 3).

### 4. Greedy control

Already the Modelfile default (`temperature 0`). Confirmed in sampler log: `temp = 0.000`.

- Greedy + short Infer prompt → **correct** CodeMode.
- Greedy + full production prompt → **wrong** payload (same as hybrid Euler).
- Therefore **not** non-greedy quantized degeneration.

Euler turn 2 (`finish_reason=stop`, 1245 output tokens) was not max-token truncation of a tool call; it was long reasoning then text asking for the lecture plan (context collapse after retry).

---

## Decision table

| Hypothesis | Verdict |
|---|---|
| Serving stack wrong; matched infer would work | **Partially open** (no GPU for `infer.py`). Unlikely to be pure template drift: templates match and OpenAI tools already parse. |
| Both stacks emit raw Manim in `run_code` | **Confirmed for production prompt.** Short Infer prompt does **not**. |
| Format correct but Manim quality collapses → E2B capacity | **Not triggered.** Format/contract fails first under the production prompt; correct format is reachable greedily. |

**Chosen next actions (before Qwen):**

1. **Clean SFT data** — filter `tool_trace` so first-turn `run_code` is overwhelmingly `wrap_then_manim_write`. Current first-call mix ≈ 99 wrap / 105 raw_manim / 121 other (334 rows). Bad rows are in-distribution.
2. **Harden production `CODE_PROMPT`** — match [`infer_tools.INFER_SYSTEM_PROMPT`](../../infer_tools.py): forbid top-level `from manim import *` in `run_code`; show a one-line correct example.
3. **Eval gate** — “GGUF ready” = greedy OpenAI `/v1` probe with production system prompt must pass CodeMode preflight, not only `animus animate` once.
4. **Optional serving hardening** — avoid native `/api/chat` tool path when args can truncate mid-JSON; keep `/v1` + adequate `max_tokens`; revisit Modelfile Go TEMPLATE vs Jinja documentation clarity.
5. **Turn-2 retry behavior** — after Monty `retry-prompt`, model can “forget” the user plan into a thinking loop; worth a follow-up (tool-result formatting / thinking channel), but not a reason to retrain on Qwen first.

**Qwen2.5-Coder-14B:** defer until a cleaned E2B re-SFT still fails CodeMode under the production prompt with greedy matched/Ollama eval.

---

## Key evidence paths

- Short correct: `raw_openai_with_tools_message.json`
- Full Euler wrong (greedy repro): `raw_openai_full_euler_message.json`
- Template identity: `ollama_template.txt` vs `apps/sft/templates/gemma4_training.jinja`
- Hybrid failure: `apps/agents/workspace/coder_runs/20260726-114637-euler-s-formula-visualization/traces/messages.json`
- Aggregate: `analysis_report.json`, `SUMMARY.md`
