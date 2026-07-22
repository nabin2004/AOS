#!/usr/bin/env python3
"""
Synthetic Prompt Generator for AOS Dataset
-----------------------------------------
Generates a large number of realistic educational user requests using the
pydantic_ai Agent defined in the provided module.

Usage:
    python generate_prompts.py --num 15000 --output prompts.jsonl --concurrency 10 --topics topics.txt

Resume support: if output file already exists, it counts existing lines and
only generates the remaining prompts.
"""

import asyncio
import json
import logging
import argparse
import random
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent

# ----------------------------------------------------------------------
# Load environment and import agent definition (from your existing code)
# ----------------------------------------------------------------------
load_dotenv()


class SFTPrompt(BaseModel):
    prompt: str


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

You will be given a specific topic. Your prompt MUST be directly about that topic.
Do not deviate from the given topic.

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

"I don't get how the attention mechanism in Transformers actually routes information. Visualize the flow of queries, keys, and values across a sequence, and maybe show how attention weights shift during decoding."

"Explain eigenvectors and eigenvalues geometrically—show a 2D transformation, then highlight the lines that stay in place. I want to see how the matrix stretches vectors along those directions."

"Can we animate a bubble sort step by step, highlighting the swaps? I want to see the array as a bar chart and the comparisons in real time."

"Show me the convolution operation in CNNs: slide a small filter over an image and illustrate the element-wise multiplications and sums to produce each output pixel."

"How does the Lorenz attractor emerge from the differential equations? Animate the trajectory in 3D while showing the system state over time—I want to see the butterfly effect."

--------------------------------------------------------------------
BAD PROMPTS (too short / vague)
--------------------------------------------------------------------

"Explain derivatives."       → no context, too generic
"Teach BFS."                 → lacks desired visual detail
"Explain PCA."               → not specific enough

--------------------------------------------------------------------
DIFFICULTY
--------------------------------------------------------------------

Vary difficulty:

introductory, intermediate, advanced undergraduate,
graduate, research intuition.

--------------------------------------------------------------------
OUTPUT
--------------------------------------------------------------------
Return ONLY the prompt.
"""

# ----------------------------------------------------------------------
# Agent setup
# ----------------------------------------------------------------------
prompt_generator = Agent(
    "openrouter:openai/gpt-5-nano",
    name="SFT Prompt Generator",
    description="Generates realistic educational user requests for the AOS synthetic dataset.",
    system_prompt=PROMPT_GENERATOR_SYSTEM,
    output_type=SFTPrompt,
)


# ----------------------------------------------------------------------
# Helper: load topics from a file (one per line)
# ----------------------------------------------------------------------
def load_topics(file_path: Path) -> List[str]:
    """Read topics from a text file, one per line. Return a list of non‑empty strings."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            topics = [line.strip() for line in f if line.strip()]
        if not topics:
            logging.warning(f"Topics file '{file_path}' is empty. Using fallback list.")
            return get_fallback_topics()
        return topics
    except FileNotFoundError:
        logging.warning(f"Topics file '{file_path}' not found. Using fallback list.")
        return get_fallback_topics()


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
# Script configuration
# ----------------------------------------------------------------------
DEFAULT_NUM_PROMPTS = 15000
DEFAULT_OUTPUT = "prompts.jsonl"
DEFAULT_CONCURRENCY = 5
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds


# ----------------------------------------------------------------------
# Async worker: generate one prompt with retries, given a topic
# ----------------------------------------------------------------------
async def generate_one_prompt(topic: str, retry_count: int = 0) -> Optional[str]:
    """Call the agent to generate a single prompt on the given topic."""
    user_message = f"Generate a user request about {topic}."
    try:
        result = await prompt_generator.run(user_message)
        # result.data is an SFTPrompt instance
        return result.output.prompt
    except Exception as e:
        logging.warning(
            f"Generation attempt {retry_count + 1} for topic '{topic}' failed: {e}"
        )
        if retry_count < MAX_RETRIES - 1:
            delay = RETRY_DELAY_BASE * (2**retry_count)
            await asyncio.sleep(delay)
            return await generate_one_prompt(topic, retry_count + 1)
        else:
            logging.error(
                f"Max retries exceeded for topic '{topic}'. Skipping one prompt."
            )
            return None


# ----------------------------------------------------------------------
# Main async generator
# ----------------------------------------------------------------------
async def generate_prompts(
    num_prompts: int,
    output_file: Path,
    concurrency: int,
    topics: List[str],
    resume: bool = True,
):
    # Count existing lines for resuming
    start_index = 0
    if resume and output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            # Count non‑empty lines
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

    # Prepare file for writing (append mode)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Semaphore to limit concurrent agent calls
    sem = asyncio.Semaphore(concurrency)
    # Lock to ensure atomic writes
    write_lock = asyncio.Lock()

    # Use tqdm if available
    try:
        from tqdm.asyncio import tqdm

        progress = tqdm(total=num_to_generate, desc="Generating prompts", unit="prompt")
    except ImportError:
        progress = None

    async def worker(task_id: int):
        """Worker that picks a random topic, generates a prompt, and writes it."""
        async with sem:
            # Pick a random topic for this prompt
            topic = random.choice(topics)
            prompt_text = await generate_one_prompt(topic)
            if prompt_text is None:
                if progress:
                    progress.update(1)
                return

            # Create a JSON object with metadata
            record = {
                "index": start_index + task_id,
                "topic": topic,
                "prompt": prompt_text,
            }
            line = json.dumps(record, ensure_ascii=False) + "\n"

            async with write_lock:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(line)
            if progress:
                progress.update(1)

    # Launch tasks
    tasks = [asyncio.create_task(worker(i)) for i in range(num_to_generate)]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logging.info("Received interrupt. Cancelling remaining tasks...")
        for t in tasks:
            t.cancel()
        # Wait for cancellation to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        logging.info("Graceful shutdown. Some prompts may not have been generated.")
    finally:
        if progress:
            progress.close()
        logging.info(
            f"Finished. Total prompts in {output_file}: {count_lines(output_file)}"
        )


def count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0


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
        help=f"Maximum concurrent agent requests (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--topics",
        type=Path,
        default="topics.txt",
        help="Path to a text file with one topic per line (default: topics.txt)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume from existing file; overwrite/start fresh.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Load topics
    topics = load_topics(args.topics)
    logging.info(
        f"Loaded {len(topics)} topics: {', '.join(topics[:5])}{' ...' if len(topics) > 5 else ''}"
    )

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # If no-resume, we can truncate or delete existing file to start fresh.
    if args.no_resume and args.output.exists():
        logging.info(f"--no-resume specified. Removing existing {args.output}")
        args.output.unlink()

    asyncio.run(
        generate_prompts(
            num_prompts=args.num,
            output_file=args.output,
            concurrency=args.concurrency,
            topics=topics,
            resume=not args.no_resume,
        )
    )


if __name__ == "__main__":
    main()
