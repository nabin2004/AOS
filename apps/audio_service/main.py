"""Demo entry point for narration generation."""

from narrator import Narrator

if __name__ == "__main__":
    narrator = Narrator(voice="alba")
    out = narrator.synthesize(
        "Hello world, this is a test of the AOS narration pipeline.",
        "narration_demo.wav",
    )
    print(f"Wrote {out} at {narrator.sample_rate} Hz")
