# Model Selection: Qwen2.5-Coder-7B-Instruct

Report-ready justification for the AlphaManimator / AOS Phase-1 SFT base model.

## Chosen base model

**[`Qwen/Qwen2.5-Coder-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)**

| Spec | Value | Relevance to this project |
|------|-------|---------------------------|
| Total parameters | 7.61B | Fits Kaggle ~20GB disk and T4/Colab QLoRA without a pipeline rebuild |
| Non-embedding parameters | 6.53B | ~1.08B is embedding/LM-head (large ~152K vocab); transformer compute is leaner |
| Layers | 28 | Comparable depth to Llama-class 8B models |
| Attention | 28 query / 4 KV (GQA) | ~½ the KV-cache of an 8-KV-head design → more headroom for batch/seq length under QLoRA |
| Context | 128K (YaRN; native ~32K) | Room for scene-spec + few-shot Manim + multi-rewrite trajectories |
| Norm / activation | RMSNorm (pre-norm) + SwiGLU | Modern stack parity with other dense instruct models |
| License | Apache 2.0 | Permissive for dissertation appendix / redistribution |

Architecture notes that matter for training: RoPE + QKV bias improve length extrapolation when prompts + generated Manim grow long; the wider FFN (intermediate size 18,944 vs narrower hidden 3584) historically favors code-pattern capacity over pure attention depth.

## Why this model (not Llama 3.1 8B)

Llama 3.1 8B is a **general chat** model whose code exposure is a slice of a mixed pretraining corpus. Qwen2.5-Coder-7B is **code-continued-pretrained** on trillions of additional code / text–code tokens on top of the Qwen2.5 base run. For research questions about syntactic correctness of Manim scenes under small-data LoRA, starting from a code-specialized prior is the stronger inductive bias.

Additional practical advantages over Llama 3.1 8B Instruct:

- Native **fill-in-the-middle (FIM)** capability from the Coder line (useful if evaluation expands to partial scene edits).
- **Dense** 7B footprint — same QLoRA tooling (PEFT/TRL/BitsAndBytes) already used in `apps/sft`, no MoE routing complexity.
- Stronger public coding-benchmark ceiling at the same size class, which is a cleaner paper claim than fine-tuning a 2024 generalist.
- Apache 2.0 vs Llama’s community license (fewer field-of-use footnotes in the ethics/IP section).

## Why not Qwen3-Coder-Next as the finetuning target

Qwen3-Coder-Next (≈80B total / ≈3B active MoE, hybrid Gated DeltaNet + attention, 256K context) is a strong **agentic coding** model, but it is the wrong LoRA target for this FYP:

1. **Research design.** The research question is whether a *small* fine-tuned model can achieve syntactic correctness + pedagogical alignment for Manim. Substituting a large MoE baseline answers a different question.
2. **MoE LoRA practicality.** Routing (many experts, sparse activation) makes LoRA harder: expert collapse, uneven gradients, and weaker PEFT/TRL support than dense Llama/Qwen stacks.
3. **Infrastructure.** Even 4-bit, ~80B params is ~40–45GB on disk — beyond the existing Kaggle 20GB disk constraint without a full storage/compute redesign.

**Correct role for Qwen3-Coder-Next:** zero-shot **teacher / synthetic-data generator** and a **strong baseline arm** in the evaluation table. Framing: *small specialized finetune vs. large general-purpose agentic coder, on pedagogical alignment specifically* — even if the 7B loses on raw SWE-style correctness.

## Why it fits AlphaManimator / AOS SFT

1. **Code prior for RQ1 (syntax).** Manim is Python with a domain DSL; a code-pretrained 7B starts closer to valid scenes than a generalist of similar size.
2. **Pedagogy is still the novel gap.** Published Qwen2.5-Coder numbers (HumanEval, MBPP, LiveCodeBench) do **not** measure Manim pedagogical alignment (voiceover structure, teaching narrative, CodeMode tool discipline). That gap is exactly what LoRA on AOS trajectories is meant to close.
3. **Training throughput under Kaggle/Colab limits.** GQA (4 KV heads) reduces activation/KV pressure vs 8-KV designs, which helps within a 9-hour timeout when using `packing=False` and long trajectories.
4. **Long-context headroom.** Multi-object pedagogical scenes with retries can run several thousand tokens; 128K (via YaRN) avoids fighting an 8K-style generation ceiling.
5. **Serving path later.** Dense Apache-2.0 weights export cleanly to GGUF/Ollama once the adapter is merged (serving currently remains on legacy Gemma until that migration lands).

## Honest caveat (include in the report)

There is **no published Manim-specific benchmark** for Qwen2.5-Coder. Base-model coding strength does not imply pedagogical Manim competence. The contribution of this project is domain SFT + evaluation on syntactic correctness and pedagogical alignment — not a claim that the base model already solves Manim teaching animations.

## References (to cite)

- Qwen2.5-Coder technical report / model card: [Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- Qwen2.5-Coder GitHub: https://github.com/QwenLM/Qwen2.5-Coder
- YaRN length extrapolation: Peng et al., arXiv:2309.00071
