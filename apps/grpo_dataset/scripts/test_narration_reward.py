from __future__ import annotations

import sys
from pathlib import Path

# Add grpo_dataset directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
GRPO_ROOT = SCRIPT_DIR.parent
if str(GRPO_ROOT) not in sys.path:
    sys.path.insert(0, str(GRPO_ROOT))

from reward_model.narration import compute_narration_score
from reward_model.aggregate import AggregateInputs, AggregateWeights, aggregate_reward

SAMPLE_SILENT_MANIM = '''
from manim import *

class CircleScene(Scene):
    def construct(self):
        c = Circle(color=BLUE)
        self.play(Create(c))
        self.wait(1)
'''

SAMPLE_NARRATED_MANIM = '''
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class NarratedCircleScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService())
        c = Circle(color=BLUE)
        
        with self.voiceover(text="Here we <bookmark mark=\'draw\'/>draw a blue circle."):
            self.wait_until_bookmark("draw")
            self.play(Create(c))
            
        with self.voiceover(text="The circle is now <bookmark mark=\'done\'/>fully rendered."):
            self.wait_until_bookmark("done")
            self.wait(1)
'''


def run_tests():
    print("Testing Narration Reward Module...\n")

    print("--- Evaluating Silent Scene ---")
    score_silent = compute_narration_score(SAMPLE_SILENT_MANIM)
    print(f"Silent Scene Narration Score: {score_silent.score:.4f}")
    print(f"Details: {score_silent.details}")
    assert score_silent.score == 0.0, f"Expected 0.0, got {score_silent.score}"

    print("\n--- Evaluating Narrated Scene ---")
    score_narrated = compute_narration_score(SAMPLE_NARRATED_MANIM)
    print(f"Narrated Scene Narration Score: {score_narrated.score:.4f}")
    print(f"Has VoiceoverScene: {score_narrated.has_voiceover_scene}")
    print(f"Has Speech Service: {score_narrated.has_speech_service}")
    print(f"Voiceover Call Count: {score_narrated.voiceover_call_count}")
    print(f"Bookmark Count: {score_narrated.bookmark_count}")
    print(f"Has Bookmark Sync: {score_narrated.has_bookmark_sync}")
    print(f"Details: {score_narrated.details}")
    assert score_narrated.score == 1.0, f"Expected 1.0, got {score_narrated.score}"

    print("\n--- Evaluating Reward Aggregation with Narration ---")
    inputs = AggregateInputs(
        executability=1.0,
        alignment_keyword=0.8,
        alignment_clip=0.85,
        coverage=0.9,
        vcer_penalty=0.0,
        narration=score_narrated.score,
    )
    weights = AggregateWeights(
        executability_gate=0.5,
        alignment_keyword=0.3,
        alignment_clip=0.2,
        coverage=0.3,
        vcer_penalty=0.1,
        narration=0.2,
    )
    result = aggregate_reward(inputs, weights)
    print(f"Aggregate Final Reward: {result.reward:.4f}")
    print(f"Breakdown: {result.breakdown}")
    assert result.reward > 0.8, f"Expected reward > 0.8, got {result.reward}"

    print("\nAll narration scoring tests passed successfully!")


if __name__ == "__main__":
    run_tests()
