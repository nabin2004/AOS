"""
GEPA — reflective prompt optimizer for the AOS classifier, powered by dspy.GEPA.

GEPA (Genetic-Pareto) evolves the classifier's instruction by reflecting on
execution traces and textual feedback rather than blindly rewriting the prompt.
See: https://arxiv.org/abs/2507.19457

Usage:
  python -m apps.agents.prompt_optimization.gepa.optimize_classifier
"""
import json
from pathlib import Path

import dspy
from dotenv import load_dotenv

from ..dspy.programs import ClassifierProgram
from ..prompts.classification import classification_instruction
from .config import GEPAConfig
from .export_prompt import export_program_instructions

load_dotenv()


def _load_examples(path: str) -> list[dspy.Example]:
    p = Path(path)
    if not p.exists():
        return []
    examples = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        example = dspy.Example(
            user_request=row["input"],
            subject=row["subject"],
            topic=row.get("topic", ""),
        ).with_inputs("user_request")
        examples.append(example)
    return examples


def classification_metric(
    gold: dspy.Example,
    pred: dspy.Prediction,
    trace=None,
    pred_name: str | None = None,
    pred_trace=None,
) -> dspy.Prediction:
    """GEPAFeedbackMetric for the classifier: scores subject accuracy + topic
    presence, and explains the miss so GEPA's reflection LM can fix it.
    """
    predicted_subject = (getattr(pred, "subject", "") or "").strip()
    predicted_topic = (getattr(pred, "topic", "") or "").strip()
    subject_ok = predicted_subject.lower() == gold.subject.strip().lower()
    topic_ok = bool(predicted_topic)
    score = (float(subject_ok) + float(topic_ok)) / 2.0

    feedback = []
    if subject_ok:
        feedback.append(f"Correct subject '{predicted_subject}'.")
    else:
        feedback.append(
            f"Wrong subject: predicted '{predicted_subject or '<empty>'}', "
            f"expected '{gold.subject}'. Re-check the domain guide "
            "(math/cs/ai/unknown) and pick the closest match."
        )
    if topic_ok:
        feedback.append(f"Topic produced: '{predicted_topic}'.")
    else:
        feedback.append(
            "Topic was empty — always produce a concise, title-cased topic "
            "with no articles or trailing punctuation."
        )

    return dspy.Prediction(score=score, feedback=" ".join(feedback))


def run_optimization(config: GEPAConfig | None = None) -> dspy.Module:
    config = config or GEPAConfig()

    dspy.configure(lm=dspy.LM(config.task_model))
    reflection_lm = dspy.LM(config.reflection_model, temperature=1.0, max_tokens=32000)

    trainset = _load_examples(config.trainset_path)
    valset = _load_examples(config.valset_path) or trainset
    if not trainset:
        raise ValueError(f"No training examples found at {config.trainset_path}")

    student = ClassifierProgram()
    student.predict.signature = student.predict.signature.with_instructions(
        classification_instruction
    )

    budget_kwargs: dict = {}
    if config.max_metric_calls is not None:
        budget_kwargs["max_metric_calls"] = config.max_metric_calls
    elif config.max_full_evals is not None:
        budget_kwargs["max_full_evals"] = config.max_full_evals
    else:
        budget_kwargs["auto"] = config.auto or "light"

    optimizer = dspy.GEPA(
        metric=classification_metric,
        reflection_lm=reflection_lm,
        reflection_minibatch_size=config.reflection_minibatch_size,
        candidate_selection_strategy=config.candidate_selection_strategy,
        use_merge=config.use_merge,
        max_merge_invocations=config.max_merge_invocations,
        num_threads=config.num_threads,
        track_stats=config.track_stats,
        log_dir=config.log_dir,
        seed=config.seed,
        **budget_kwargs,
    )

    optimized = optimizer.compile(student, trainset=trainset, valset=valset)

    for pred_name, path in export_program_instructions(
        optimized, "classifier_optimized", config.output_dir
    ).items():
        print(f"Saved optimized instructions for '{pred_name}' -> {path}")

    if config.track_stats and getattr(optimized, "detailed_results", None) is not None:
        results = optimized.detailed_results
        print(f"Best aggregate validation score: {results.val_aggregate_scores[results.best_idx]:.3f}")

    return optimized


if __name__ == "__main__":
    run_optimization()
