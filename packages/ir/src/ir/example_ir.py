"""
Golden example + validator smoke test.

Builds a slice of the Euler's-formula lecture described from Grant
Sanderson's talk (unit circle -> e^{i pi} = -1 -> i^2 = -1 -> a+bi on the
complex plane), then deliberately breaks three rules to show the guards fire.
"""
from .manim_ir import (
    AmbientAnimation, AmbientType, Beat, Branding, Camera, EntityType,
    Lecture, LectureIR, NarrationSegment, Operation, OperationType, Position,
    Scene, SceneObject, Storyboard, StoryboardStep, StoryboardMove, Style,
    Subject, Direction, CognitiveLoadPolicy,
)
from pydantic import ValidationError


def build_euler() -> LectureIR:
    # --- Scene 1: the unit circle and Euler's identity ---
    scene1 = Scene(
        id="s_circle",
        title="The unit circle & Euler's identity",
        scene_graph=[
            SceneObject(id="circle", entity_type=EntityType.CIRCLE,
                        position=Position(x=-3, y=0),
                        style=Style(color="#3B82F6"),
                        params={"radius": 1.5}),
            SceneObject(id="radius", entity_type=EntityType.LINE,
                        position=Position(x=-3, y=0),
                        style=Style(color="#F59E0B")),
            SceneObject(id="euler", entity_type=EntityType.MATH_TEX,
                        position=Position(x=3, y=1),
                        params={"tex": r"e^{i\pi} = -1"}),
            SceneObject(id="isq", entity_type=EntityType.MATH_TEX,
                        position=Position(next_to="euler", direction=Direction.DOWN),
                        params={"tex": r"i^2 = -1"}),
        ],
        beats=[
            Beat(
                animation_segment=[
                    Operation(target="circle", op=OperationType.CREATE, run_time=1.5),
                    Operation(target="radius", op=OperationType.CREATE,
                              run_time=1.0, with_previous=True),
                ],
                narration=NarrationSegment(text="Let's start with the unit circle."),
                hold_seconds=1.0,
                ambient=[AmbientAnimation(type=AmbientType.CAMERA_DRIFT)],
            ),
            Beat(  # one new equation — within the cognitive-load budget
                animation_segment=[
                    Operation(target="euler", op=OperationType.WRITE, run_time=1.5),
                ],
                narration=NarrationSegment(
                    text="This is Euler's identity. It ties together e, i, "
                         "pi, one and zero in a single line.",
                    emphasis=["Euler's identity"],
                ),
                hold_seconds=2.0,
            ),
            Beat(  # highlight is emphasis, not a new object
                animation_segment=[
                    Operation(target="euler", op=OperationType.HIGHLIGHT, run_time=1.0),
                    Operation(target="isq", op=OperationType.WRITE, run_time=1.2),
                ],
                narration=NarrationSegment(
                    text="And it all rests on this: i squared equals minus one."),
                hold_seconds=1.5,
            ),
        ],
    )

    # --- Scene 2: the complex plane (reusable across many lectures) ---
    scene2 = Scene(
        id="s_plane",
        title="The complex plane",
        reusable=True,
        scene_graph=[
            SceneObject(id="plane", entity_type=EntityType.COMPLEX_PLANE,
                        visible=True),  # pre-filled: already on screen on entry
            SceneObject(id="pt", entity_type=EntityType.MATH_TEX,
                        position=Position(x=2, y=2),
                        params={"tex": "a+bi"}),
        ],
        beats=[
            Beat(
                animation_segment=[
                    Operation(target="pt", op=OperationType.WRITE, run_time=1.5),
                ],
                narration=NarrationSegment(
                    text="Every complex number a plus b i is just a point here."),
                hold_seconds=2.0,
            ),
        ],
    )

    return LectureIR(
        manim_version="0.18.1",
        branding=Branding(brand_name="AOS", tagline="by Nabin :-)"),
        lecture=Lecture(
            topic="Euler's Formula",
            subject=Subject.MATH,
            assumptions=["You know what the unit circle is."],
            objectives=["Understand why e^{i pi} = -1."],
            opener="Most people meet this formula as a magic trick. It isn't.",
            learning_outcomes=["Read Euler's identity geometrically."],
        ),
        storyboard=Storyboard(
            goal="Introduce Euler's formula",
            steps=[
                StoryboardStep(move=StoryboardMove.INTRODUCE,
                               goal="Anchor on the unit circle", scene_id="s_circle"),
                StoryboardStep(move=StoryboardMove.CONNECT,
                               goal="Land it in the complex plane", scene_id="s_plane"),
            ],
        ),
        scenes=[scene1, scene2],
    )


def expect_failure(label: str, fn) -> None:
    try:
        fn()
    except ValidationError as e:
        msg = e.errors()[0]["msg"]
        print(f"  REJECTED ({label}): {msg}")
    else:
        print(f"  !! NOT REJECTED ({label}) — guard failed")


if __name__ == "__main__":
    ir = build_euler()
    print("VALID lecture built.")
    print(f"  scenes: {len(ir.scenes)}  total duration ~ {ir.duration_seconds}s")
    print(f"  scene1 duration ~ {ir.scenes[0].duration_seconds}s")

    print("\nNegative tests (each SHOULD be rejected):")

    # 1. operate on an object before creating it
    expect_failure("op before create", lambda: Scene(
        id="bad1",
        scene_graph=[SceneObject(id="c", entity_type=EntityType.CIRCLE)],
        beats=[Beat(animation_segment=[
            Operation(target="c", op=OperationType.MOVE)])],
    ))

    # 2. too many new equations in one beat (cognitive load: max 1)
    expect_failure("2 equations in a beat", lambda: Scene(
        id="bad2",
        scene_graph=[
            SceneObject(id="e1", entity_type=EntityType.MATH_TEX),
            SceneObject(id="e2", entity_type=EntityType.MATH_TEX),
        ],
        beats=[Beat(animation_segment=[
            Operation(target="e1", op=OperationType.WRITE),
            Operation(target="e2", op=OperationType.WRITE)])],
    ))

    # 3. object placed off the safe frame
    expect_failure("off-frame position",
                   lambda: Position(x=99, y=0))

    # 4. storyboard references a scene that doesn't exist
    expect_failure("dangling storyboard ref", lambda: LectureIR(
        lecture=Lecture(topic="x", subject=Subject.CS),
        storyboard=Storyboard(goal="g", steps=[
            StoryboardStep(move=StoryboardMove.INTRODUCE, goal="g",
                           scene_id="ghost")]),
        scenes=[],
    ))

    # Show the load policy is overridable per-lecture via validation context
    print("\nStricter policy via context (max_new_objects_per_beat=1):")
    strict = CognitiveLoadPolicy(max_new_objects_per_beat=1)
    expect_failure("2 objects under strict policy", lambda: Scene.model_validate(
        {
            "id": "strict",
            "scene_graph": [
                {"id": "a", "entity_type": "circle"},
                {"id": "b", "entity_type": "square"},
            ],
            "beats": [{"animation_segment": [
                {"target": "a", "op": "create"},
                {"target": "b", "op": "create"}]}],
        },
        context={"load_policy": strict},
    ))

    print("\nRound-trip JSON schema export works:", bool(LectureIR.model_json_schema()))