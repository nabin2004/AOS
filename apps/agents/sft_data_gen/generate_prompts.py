#!/usr/bin/env python3
"""
Synthetic Prompt Generator for AOS Dataset
-----------------------------------------
Generates a large number of realistic educational user requests using the
pydantic_ai Agent defined in the provided module.

Usage:
    python generate_prompts.py --num 8000 --output prompts.jsonl --concurrency 20 \
        --topics topics.txt additional_topics.txt andrej_karpathy.txt --no-resume

Resume support: if output file already exists, it counts existing lines and
only generates the remaining prompts.
"""

import asyncio
import json
import logging
import argparse
import random
import re
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# ----------------------------------------------------------------------
# Load environment and import agent definition (from your existing code)
# ----------------------------------------------------------------------
_AGENTS_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_AGENTS_ROOT / ".env")
load_dotenv()


class SFTPromptItem(BaseModel):
    topic: str
    prompt: str


class SFTPromptBatch(BaseModel):
    prompts: List[SFTPromptItem] = Field(default_factory=list)


# ----------------------------------------------------------------------
# SYSTEM PROMPT – encourages rich, concise, natural requests
# ----------------------------------------------------------------------
PROMPT_GENERATOR_SYSTEM = """
You are generating high-quality synthetic USER REQUESTS for the AOS
(Autonomous Open School) dataset.

The requests will later be consumed by:

1. Subject Classifier
2. Lecture Planner
3. Manim Coding Agent

Your job is ONLY to write realistic user requests.

The requests should resemble what a real instructor, student, engineer,
or learner would ask.

--------------------------------------------------------------------
PRIMARY GOAL
--------------------------------------------------------------------

Generate prompts that force the downstream pipeline to produce rich,
educational Manim animations.

Every prompt should naturally require planning, scene decomposition,
mathematical reasoning, and programmatic visualization.

Make prompts concise and natural—typically **3–5 lines** (max 7, rarely up to 10).

Avoid toy examples.

Avoid mentioning internal pipeline components.

Do NOT mention Lecture, IR, JSON, Pydantic, or implementation details.

Pretend you are a real user requesting an educational video.

--------------------------------------------------------------------
TOPIC
--------------------------------------------------------------------

You will be given one or more specific topics. Each prompt MUST be
directly about its assigned topic. Do not deviate from the given topic.

--------------------------------------------------------------------
VOICE / ROLE (CRITICAL — follow exactly)
--------------------------------------------------------------------

Pick ONE clear voice per prompt. Never mix them.

**Instructor voice** — when naming an audience or course you deliver:
- Use "I'm teaching … to undergrads/students…"
- Use "I'm teaching an undergrad/graduate course on …"
- NEVER write "I'm learning … students" or "I'm learning X to undergraduates"
- NEVER write "I'm learning an undergrad course on …" (that is instructor framing;
  say "I'm teaching an undergrad course on …" instead)

**Student / learner voice** — when the speaker is studying the subject:
- Use "I'm learning …", "I want to understand…", "I've always struggled with…"
- The object of "learning" must be the SUBJECT (linear algebra, FFT, SGD),
  never an audience ("students", "undergrads")

GOOD instructor:
"I'm teaching undergrad ML students and want a vivid visualization of optimization dynamics."

GOOD student:
"I'm learning linear algebra and want a visual that builds intuition for eigenvectors."

BAD (never produce):
"I'm learning undergrad ML students and want…"
"I'm learning linear algebra to undergraduates…"
"I'm learning an undergrad course on SVD…"

--------------------------------------------------------------------
PROMPT STYLE
--------------------------------------------------------------------

Write in natural English.

The request should feel like something a professor, educator,
or curious learner would actually ask a Manim animation system.

Do not write bullet lists unless the user would naturally do so.

Vary the **length**:
- Short: 2–3 lines (direct question)
- Medium: 4–6 lines (with context and desired visual)
- Long: 7–10 lines (more detailed, for complex topics)

Vary the **tone**:
- Confused: "I never quite understood..."
- Curious: "I wonder what it would look like if..."
- Direct: "Create a visual that shows..."
- Exploratory: "Can we animate how ... changes when ..."

Across a batch, mix instructor and student voices (roughly half and half).

--------------------------------------------------------------------
WHAT TO INCLUDE (naturally woven in)
--------------------------------------------------------------------

The request should implicitly cover some of these—but don't force them:

• target audience
• prerequisite knowledge
• desired depth
• teaching style
• pacing
• visual style
• preferred examples
• intuition
• mathematical rigor
• motivation
• real-world applications
• historical context
• common misconceptions
• comparison with related concepts
• interactive thought experiments

--------------------------------------------------------------------
ENCOURAGE COMPLEX VISUALIZATIONS (naturally)
--------------------------------------------------------------------

Whenever appropriate, ask for:

• multiple scenes • transitions • diagrams • graphs • plots
• geometric constructions • animated equations • simulations
• parameter sweeps • camera motion • zooming • rotating objects
• 3D visualizations • timelines • algorithm walkthroughs

Do NOT explicitly say "use camera operations". Write naturally:

"I'd like the camera to orbit the object..."
"I want to zoom into the surface..."

--------------------------------------------------------------------
ENCOURAGE EXTERNAL LIBRARIES (naturally)
--------------------------------------------------------------------

When the topic benefits from computation, motivate why numerical
simulation is necessary (for Manim).

Examples:
- Lorenz attractor → scipy.integrate.solve_ivp
- Shortest paths → networkx
- Optimization → numpy
- Probability → scipy.stats
- Machine learning → numpy
- Signal processing → scipy.signal
- Graphs → networkx

Don't mention the library by name; instead, say "I want to see the actual trajectory over time" or "show the probability distribution evolving".

--------------------------------------------------------------------
ENCOURAGE MANIM FEATURES (naturally)
--------------------------------------------------------------------

Prompt should naturally lead to use of:
ValueTracker, always_redraw, TracedPath, Axes, ThreeDAxes,
Surface, NumberPlane, VectorField, StreamLines, Graph, Brace,
Angle, MathTex, Tex, Code, Table, BarChart, ImplicitFunction,
ComplexPlane, camera movement, MovingCameraScene, ThreeDScene,
voiceover sync, scene transitions.

Don't list them—ask for the visual effect.

--------------------------------------------------------------------
FORMULAS
--------------------------------------------------------------------

Encourage deriving or displaying formulas visually when relevant,
but this is optional.

--------------------------------------------------------------------
EXCELLENT EXAMPLES (short and realistic)
--------------------------------------------------------------------

(These are examples; adapt to your given topic.)

"I've always struggled with why gradient descent sometimes overshoots. Can you animate the loss surface and show the optimizer path for different learning rates? I'd love to see how the step size affects convergence or divergence."

"I'm teaching an undergrad course on Decision-Theoretic Planning and want a visual that walks through belief updates over a small POMDP, with intuition first then the Bellman backup."

"I don't get how the attention mechanism in Transformers actually routes information. Visualize the flow of queries, keys, and values across a sequence, and maybe show how attention weights shift during decoding."

"Explain eigenvectors and eigenvalues geometrically—show a 2D transformation, then highlight the lines that stay in place. I want to see how the matrix stretches vectors along those directions."

"Can we animate a bubble sort step by step, highlighting the swaps? I want to see the array as a bar chart and the comparisons in real time."

"Show me the convolution operation in CNNs: slide a small filter over an image and illustrate the element-wise multiplications and sums to produce each output pixel."

"How does the Lorenz attractor emerge from the differential equations? Animate the trajectory in 3D while showing the system state over time—I want to see the butterfly effect."

--------------------------------------------------------------------
BAD PROMPTS (too short / vague / wrong voice)
--------------------------------------------------------------------

"Explain derivatives."       → no context, too generic
"Teach BFS."                 → lacks desired visual detail
"Explain PCA."               → not specific enough
"I'm learning undergrad ML students…" → teaching→learning swap; forbidden
"generate a user request for the AOS dataset…" → meta leak; forbidden

--------------------------------------------------------------------
DIFFICULTY
--------------------------------------------------------------------

Vary difficulty:

introductory, intermediate, advanced undergraduate,
graduate, research intuition.

--------------------------------------------------------------------
OUTPUT
--------------------------------------------------------------------
Return structured prompts only — one entry per assigned topic.
Do not wrap prompts in quotes or markdown fences.
"""

# ----------------------------------------------------------------------
# Agent setup
# ----------------------------------------------------------------------
prompt_generator = Agent(
    "openrouter:openai/gpt-5-nano",
    name="SFT Prompt Generator",
    description="Generates realistic educational user requests for the AOS synthetic dataset.",
    system_prompt=PROMPT_GENERATOR_SYSTEM,
    output_type=SFTPromptBatch,
)


# ----------------------------------------------------------------------
# Topic seed cleaning
# ----------------------------------------------------------------------
_TOPIC_WRAPPERS = [
    re.compile(r"^I want to learn about the \((.+)\)\s*$", re.I),
    re.compile(r"^I want to learn about the (.+)$", re.I),
    re.compile(r"^I want to learn about (.+)$", re.I),
    re.compile(r"^Teach me about the \((.+)\)\s*$", re.I),
    re.compile(r"^Teach me about the (.+)$", re.I),
    re.compile(r"^Teach me about (.+)$", re.I),
    re.compile(r"^I['’]m learning about the \((.+)\)\s*$", re.I),
    re.compile(r"^I['’]m learning about (.+)$", re.I),
    re.compile(r"^I['’]m teaching about the \((.+)\)\s*$", re.I),
    re.compile(r"^I['’]m teaching about (.+)$", re.I),
]


def normalize_topic(raw: str) -> Tuple[str, bool]:
    """Strip prompt-like wrappers from a seed line. Returns (topic, was_normalized)."""
    t = raw.strip()
    if not t:
        return "", False
    for pat in _TOPIC_WRAPPERS:
        m = pat.match(t)
        if m:
            inner = m.group(1).strip()
            if inner.startswith("(") and inner.endswith(")"):
                inner = inner[1:-1].strip()
            return inner, True
    return t, False


def load_topics(file_path: Path) -> Tuple[List[str], int]:
    """Read topics from a text file, normalizing wrappers. Returns (topics, normalized_count)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
    except FileNotFoundError:
        logging.warning(f"Topics file '{file_path}' not found.")
        return [], 0

    topics: List[str] = []
    normalized = 0
    for line in lines:
        topic, was = normalize_topic(line)
        if was:
            normalized += 1
        if topic:
            topics.append(topic)
    if not topics:
        logging.warning(f"Topics file '{file_path}' is empty.")
    return topics, normalized


def load_topics_many(file_paths: List[Path]) -> List[str]:
    """Load, normalize, and case-insensitively dedupe topics (order preserved)."""
    seen: set[str] = set()
    topics: List[str] = []
    total_normalized = 0
    for path in file_paths:
        loaded, normalized = load_topics(path)
        total_normalized += normalized
        for topic in loaded:
            key = topic.casefold()
            if key not in seen:
                seen.add(key)
                topics.append(topic)
    if total_normalized:
        logging.info(
            f"Normalized {total_normalized} wrapped seed line(s) to bare topics."
        )
    if not topics:
        logging.warning("No topics loaded from any file. Using fallback list.")
        return get_fallback_topics()
    return topics


def get_fallback_topics() -> List[str]:
    """Fallback topics if the file is missing or empty."""
    return [
        "Mathematics",
        "Linear Algebra",
        "Calculus",
        "Probability",
        "Statistics",
        "Optimization",
        "Algorithms",
        "Data Structures",
        "Operating Systems",
        "Networks",
        "Compilers",
        "Machine Learning",
        "Deep Learning",
        "Transformers",
        "Reinforcement Learning",
        "Computer Vision",
        "NLP",
        "Distributed Systems",
        "GPU Computing",
        "Scientific Computing",
        "Numerical Analysis",
        "Physics",
        "Mechanics",
        "Electromagnetism",
        "Quantum Mechanics",
        "Thermodynamics",
        "Signal Processing",
        "Control Systems",
        "Robotics",
        "Computer Graphics",
        "Databases",
        "Cryptography",
        "Information Theory",
    ]


# ----------------------------------------------------------------------
# Quality gate
# ----------------------------------------------------------------------
_RE_LEARNING_AUDIENCE = re.compile(
    r"I['’]m learning\s+"
    r"(?:"
    r"undergrads?\b|undergraduates?\b|graduates?\b|"
    r".{0,60}?\bstudents\b|"
    r".{0,50}?\bto\s+(?:undergraduates?|undergrads?|students|upper[- ]level|"
    r"upper[- ]undergraduate|graduate\s+students)"
    r")",
    re.I | re.S,
)
_RE_LEARNING_COURSE = re.compile(
    r"I['’]m learning\s+(?:an?\s+)?(?:undergrad(?:uate)?|graduate|upper[- ]level|"
    r"advanced)\s+(?:course|module|class|unit)\b",
    re.I,
)
_RE_META_LEAK = re.compile(
    r"(?:AOS\s+dataset|generate\s+a\s+(?:single\s+)?(?:high-quality\s+)?"
    r"user\s+request|for\s+the\s+AOS)",
    re.I,
)


def prompt_quality_issue(prompt: str) -> Optional[str]:
    """Return a short reject reason, or None if the prompt is acceptable."""
    text = (prompt or "").strip()
    if len(text) < 40:
        return "too_short"
    if _RE_META_LEAK.search(text):
        return "meta_leak"
    if _RE_LEARNING_AUDIENCE.search(text):
        return "learning_audience_swap"
    if _RE_LEARNING_COURSE.search(text):
        return "learning_course_frame"
    return None


# ----------------------------------------------------------------------
# Script configuration
# ----------------------------------------------------------------------
DEFAULT_NUM_PROMPTS = 8000
DEFAULT_OUTPUT = "prompts.jsonl"
DEFAULT_CONCURRENCY = 20
DEFAULT_BATCH_SIZE = 8
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds


# ----------------------------------------------------------------------
# Async worker: generate a batch of prompts with retries
# ----------------------------------------------------------------------
async def generate_prompt_batch(
    topics: List[str], retry_count: int = 0
) -> Optional[List[SFTPromptItem]]:
    """Call the agent to generate one user request per topic."""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(topics))
    user_message = (
        f"Generate exactly {len(topics)} user requests, one for each topic below.\n"
        f"Return one prompt per topic in the same order.\n\n"
        f"Topics:\n{numbered}"
    )
    try:
        result = await prompt_generator.run(user_message)
        items = list(result.output.prompts)
        # Align length: pad/trim by assigned topic if model drifts
        aligned: List[SFTPromptItem] = []
        for i, topic in enumerate(topics):
            if i < len(items) and items[i].prompt.strip():
                aligned.append(
                    SFTPromptItem(topic=topic, prompt=items[i].prompt.strip())
                )
            else:
                # Try match by topic string
                match = next(
                    (
                        it
                        for it in items
                        if it.topic.strip().casefold() == topic.casefold()
                    ),
                    None,
                )
                if match and match.prompt.strip():
                    aligned.append(
                        SFTPromptItem(topic=topic, prompt=match.prompt.strip())
                    )
                else:
                    aligned.append(SFTPromptItem(topic=topic, prompt=""))
        return aligned
    except Exception as e:
        logging.warning(
            f"Batch generation attempt {retry_count + 1} failed "
            f"({len(topics)} topics): {e}"
        )
        if retry_count < MAX_RETRIES - 1:
            delay = RETRY_DELAY_BASE * (2**retry_count)
            await asyncio.sleep(delay)
            return await generate_prompt_batch(topics, retry_count + 1)
        logging.error(
            f"Max retries exceeded for batch of {len(topics)} topics. Skipping batch."
        )
        return None


async def generate_valid_batch(
    topics: List[str],
    reject_counts: dict,
) -> List[SFTPromptItem]:
    """Generate a batch and retry rejected prompts individually until valid or exhausted."""
    batch = await generate_prompt_batch(topics)
    if batch is None:
        return []

    accepted: List[SFTPromptItem] = []
    for item in batch:
        issue = prompt_quality_issue(item.prompt)
        if issue is None:
            accepted.append(item)
            continue
        reject_counts[issue] = reject_counts.get(issue, 0) + 1
        logging.debug(
            f"Rejected prompt for topic '{item.topic}' ({issue}); retrying singly."
        )
        # Single-topic retry with quality gate
        recovered = None
        for attempt in range(MAX_RETRIES):
            single = await generate_prompt_batch([item.topic])
            if not single:
                continue
            cand = single[0]
            issue2 = prompt_quality_issue(cand.prompt)
            if issue2 is None:
                recovered = cand
                break
            reject_counts[issue2] = reject_counts.get(issue2, 0) + 1
            await asyncio.sleep(RETRY_DELAY_BASE * (2**attempt))
        if recovered:
            accepted.append(recovered)
        else:
            logging.warning(
                f"Dropping topic '{item.topic}' after quality-gate failures."
            )
    return accepted


# ----------------------------------------------------------------------
# Main async generator
# ----------------------------------------------------------------------
async def generate_prompts(
    num_prompts: int,
    output_file: Path,
    concurrency: int,
    topics: List[str],
    batch_size: int = DEFAULT_BATCH_SIZE,
    resume: bool = True,
):
    # Count existing lines for resuming
    start_index = 0
    if resume and output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing = sum(1 for line in f if line.strip())
        if existing >= num_prompts:
            logging.info(
                f"Output file already has {existing} prompts, which meets the requested {num_prompts}. Exiting."
            )
            return
        start_index = existing
        num_to_generate = num_prompts - existing
        logging.info(
            f"Resuming: found {existing} existing prompts. Will generate {num_to_generate} more."
        )
    else:
        num_to_generate = num_prompts
        logging.info(f"Starting fresh. Generating {num_to_generate} prompts.")

    if num_to_generate <= 0:
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    reject_counts: dict = {}
    next_index = start_index
    written = 0
    written_lock = asyncio.Lock()

    try:
        from tqdm.asyncio import tqdm

        progress = tqdm(total=num_to_generate, desc="Generating prompts", unit="prompt")
    except ImportError:
        progress = None

    # Build topic batches covering num_to_generate slots
    topic_batches: List[List[str]] = []
    remaining = num_to_generate
    while remaining > 0:
        size = min(batch_size, remaining)
        topic_batches.append([random.choice(topics) for _ in range(size)])
        remaining -= size

    async def append_items(items: List[SFTPromptItem]) -> int:
        """Write items up to the remaining quota. Returns how many were written."""
        nonlocal next_index, written
        lines: List[str] = []
        async with written_lock:
            for item in items:
                if written >= num_to_generate:
                    break
                record = {
                    "index": next_index,
                    "topic": item.topic,
                    "prompt": item.prompt,
                }
                lines.append(json.dumps(record, ensure_ascii=False) + "\n")
                next_index += 1
                written += 1
        if lines:
            async with write_lock:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.writelines(lines)
            if progress:
                progress.update(len(lines))
        return len(lines)

    async def worker(batch_topics: List[str]):
        async with sem:
            items = await generate_valid_batch(batch_topics, reject_counts)
            if items:
                await append_items(items)

    tasks = [asyncio.create_task(worker(b)) for b in topic_batches]
    try:
        await asyncio.gather(*tasks)

        # Top up if quality-gate drops left us short of the target
        topup_rounds = 0
        while written < num_to_generate and topup_rounds < 50:
            need = num_to_generate - written
            size = min(batch_size, need)
            fill_topics = [random.choice(topics) for _ in range(size)]
            async with sem:
                items = await generate_valid_batch(fill_topics, reject_counts)
            if not items:
                topup_rounds += 1
                continue
            n = await append_items(items)
            if n == 0:
                break
            topup_rounds += 1
        if written < num_to_generate:
            logging.warning(
                f"Stopped at {written}/{num_to_generate} prompts after top-up attempts."
            )
    except KeyboardInterrupt:
        logging.info("Received interrupt. Cancelling remaining tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logging.info("Graceful shutdown. Some prompts may not have been generated.")
    finally:
        if progress:
            progress.close()
        if reject_counts:
            logging.info(
                "Quality-gate rejects: "
                + ", ".join(f"{k}={v}" for k, v in sorted(reject_counts.items()))
            )
        logging.info(
            f"Finished. Total prompts in {output_file}: {count_lines(output_file)}"
        )


def count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0


def verify_prompts(path: Path, sample: int = 20) -> None:
    """Log alignment stats and a random sample after generation."""
    if not path.exists():
        logging.warning(f"Cannot verify; {path} missing.")
        return

    total = 0
    teaching = 0
    learning = 0
    bad = 0
    prompts: List[dict] = []
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        obj = json.loads(line)
        total += 1
        prompts.append(obj)
        p = obj.get("prompt", "")
        if re.search(r"I['’]m teaching", p, re.I):
            teaching += 1
        if re.search(r"I['’]m learning", p, re.I):
            learning += 1
        if prompt_quality_issue(p):
            bad += 1

    logging.info(
        f"Verify: total={total} teaching={teaching} learning={learning} "
        f"quality_failures={bad}"
    )
    if prompts and sample > 0:
        for obj in random.sample(prompts, min(sample, len(prompts))):
            preview = obj["prompt"].replace("\n", " / ")[:160]
            logging.info(f"  sample[{obj.get('index')}] {preview}")


# ----------------------------------------------------------------------
# Command line entry point
# ----------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic educational prompts."
    )
    parser.add_argument(
        "--num",
        type=int,
        default=DEFAULT_NUM_PROMPTS,
        help=f"Total number of prompts to have in the output file (default: {DEFAULT_NUM_PROMPTS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSONL file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Maximum concurrent batch API requests (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Topics per API call (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--topics",
        type=Path,
        nargs="+",
        default=[Path("topics.txt")],
        help="One or more topic seed files (default: topics.txt)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume from existing file; backup and start fresh.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After generation, print alignment stats and a random sample.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    topics = load_topics_many(list(args.topics))
    logging.info(
        f"Loaded {len(topics)} topics from {len(args.topics)} file(s): "
        f"{', '.join(topics[:5])}{' ...' if len(topics) > 5 else ''}"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.no_resume and args.output.exists():
        bak = args.output.with_suffix(args.output.suffix + ".bak")
        logging.info(f"--no-resume: backing up {args.output} → {bak}")
        shutil.copy2(args.output, bak)
        args.output.unlink()
        logging.info(f"Removed existing {args.output}")

    asyncio.run(
        generate_prompts(
            num_prompts=args.num,
            output_file=args.output,
            concurrency=args.concurrency,
            topics=topics,
            batch_size=args.batch_size,
            resume=not args.no_resume,
        )
    )

    if args.verify:
        verify_prompts(args.output)


if __name__ == "__main__":
    main()
