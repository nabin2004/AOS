"""
Golden example + validator smoke test (v2).

Two lectures' worth of slices:

  build_euler()  — the original unit-circle -> e^{i pi} = -1 slice, now with
                   class names, rate functions and a TransformFromCopy.
  build_lorenz() — a Lorenz attractor: warm up in 2D, pan the camera into
                   3D, draw the trajectory from a scipy.solve_ivp
                   Computation, leave a traced tail + a glowing endpoint dot,
                   with a rho ValueTracker as a runtime knob.

Then we deliberately break the guards (old and new) to show they fire.
"""
from manim_ir import (
    AmbientAnimation, AmbientType, Beat, Behavior, BehaviorType, Branding,
    Camera, CognitiveLoadPolicy, ComputeLibrary, Computation, Direction,
    EntityType, Lecture, LectureIR, NarrationSegment, Operation,
    OperationType, Position, Quality, RateFunction, RenderConfig, Scene,
    SceneObject, SceneParameter, Storyboard, StoryboardMove, StoryboardStep,
    Style, Subject, SymbolSource, ValueTracker, CAMERA_TARGET,
)
from pydantic import ValidationError


def build_euler() -> LectureIR:
    scene1 = Scene(
        id="s_circle",
        class_name="UnitCircleEuler",
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
                        # pull the canonical form from Wikipedia
                        symbol_source=SymbolSource.WIKIPEDIA,
                        symbol_query="Euler's identity",
                        params={"tex": r"e^{i\pi} = -1"}),
            SceneObject(id="isq", entity_type=EntityType.MATH_TEX,
                        position=Position(next_to="euler", direction=Direction.DOWN),
                        params={"tex": r"i^2 = -1"}),
        ],
        beats=[
            Beat(
                animation_segment=[
                    Operation(target="circle", op=OperationType.CREATE,
                              run_time=1.5, rate_func=RateFunction.EASE_IN_OUT),
                    Operation(target="radius", op=OperationType.CREATE,
                              run_time=1.0, with_previous=True),
                ],
                narration=NarrationSegment(text="Let's start with the unit circle."),
                hold_seconds=1.0,
                ambient=[AmbientAnimation(type=AmbientType.CAMERA_DRIFT)],
            ),
            Beat(
                animation_segment=[
                    Operation(target="euler", op=OperationType.WRITE,
                              run_time=1.5, rate_func=RateFunction.SMOOTH),
                ],
                narration=NarrationSegment(
                    text="This is Euler's identity. It ties together e, i, "
                         "pi, one and zero in a single line.",
                    emphasis=["Euler's identity"],
                ),
                hold_seconds=2.0,
            ),
            Beat(
                # i^2=-1 is *derived* from euler as a copy — TransformFromCopy
                animation_segment=[
                    Operation(target="euler", op=OperationType.CIRCUMSCRIBE,
                              run_time=1.0),
                    Operation(target="isq", op=OperationType.TRANSFORM_FROM_COPY,
                              run_time=1.2, params={"source": "euler"}),
                ],
                narration=NarrationSegment(
                    text="And it all rests on this: i squared equals minus one."),
                hold_seconds=1.5,
            ),
        ],
    )

    scene2 = Scene(
        id="s_plane",
        class_name="ComplexPlanePoint",
        title="The complex plane",
        reusable=True,
        scene_graph=[
            SceneObject(id="plane", entity_type=EntityType.COMPLEX_PLANE,
                        visible=True),
            SceneObject(id="pt", entity_type=EntityType.MATH_TEX,
                        position=Position(x=2, y=2),
                        params={"tex": "a+bi"}),
        ],
        beats=[
            Beat(
                animation_segment=[
                    Operation(target="pt", op=OperationType.WRITE,
                              run_time=1.5, rate_func=RateFunction.RUSH_INTO),
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
        render=RenderConfig(quality=Quality.HIGH, fps=60),
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


def build_lorenz() -> LectureIR:
    """3D done right: start flat, pan into depth, trajectory from real maths."""
    scene = Scene(
        id="s_lorenz",
        class_name="LorenzAttractor",
        title="The Lorenz attractor",
        template=None,
        is_3d=True,
        begin_in_2d=True,
        camera=Camera(is_3d=True, phi=0.0, theta=0.0),  # start face-on (flat)
        runtime_params=[
            SceneParameter(name="rho", py_type="float", default=28.0,
                           description="Rayleigh number; 28 is the classic butterfly."),
            SceneParameter(name="t_end", py_type="float", default=40.0),
        ],
        trackers=[
            ValueTracker(id="rho", initial=28.0, min_value=0.0, max_value=60.0,
                         label="rho"),
        ],
        computations=[
            Computation(
                id="lorenz_traj",
                library=ComputeLibrary.SCIPY,
                routine="solve_ivp",
                params={"sigma": 10.0, "rho": 28.0, "beta": 8 / 3,
                        "y0": [1.0, 1.0, 1.0], "t_end": 40.0, "n": 6000},
                produces="Lorenz trajectory, (N,3) array of xyz points",
            ),
        ],
        scene_graph=[
            SceneObject(id="axes", entity_type=EntityType.THREE_D_AXES,
                        visible=True, label="ThreeDAxes; flat at first"),
            SceneObject(id="eq", entity_type=EntityType.MATH_TEX,
                        position=Position(x=-5, y=3),
                        fix_in_frame=True,   # keep facing the camera in 3D
                        symbol_source=SymbolSource.WIKIPEDIA,
                        symbol_query="Lorenz system",
                        params={"tex": r"\dot{x}=\sigma(y-x)"}),
            # the trajectory itself, sampled from the computation above
            SceneObject(id="curve", entity_type=EntityType.PARAMETRIC_CURVE,
                        computation="lorenz_traj",
                        style=Style(color="#10B981", stroke_width=2.0),
                        behaviors=[
                            # leave a fading tail as it draws
                            Behavior(type=BehaviorType.TRACE_PATH),
                        ]),
            # a glowing dot pinned to the leading end of the curve
            SceneObject(id="head", entity_type=EntityType.DOT,
                        style=Style(color="#F59E0B", glow=True),
                        behaviors=[
                            Behavior(type=BehaviorType.TRACK_ENDPOINT, of="curve"),
                            Behavior(type=BehaviorType.GLOW_PULSE),
                        ]),
        ],
        beats=[
            Beat(  # 1. establish the equation, flat
                animation_segment=[
                    Operation(target="eq", op=OperationType.WRITE, run_time=1.5),
                ],
                narration=NarrationSegment(
                    text="Three simple coupled equations. Watch what they do."),
                hold_seconds=1.0,
            ),
            Beat(  # 2. pan into 3D — reveal depth, don't snap to it
                animation_segment=[
                    Operation(target=CAMERA_TARGET,
                              op=OperationType.SET_CAMERA_ORIENTATION,
                              run_time=2.0, rate_func=RateFunction.SMOOTH,
                              params={"phi": 1.15, "theta": -0.6}),
                ],
                narration=NarrationSegment(
                    text="Let's tilt into three dimensions."),
                hold_seconds=0.5,
            ),
            Beat(  # 3. draw the trajectory; tail + glowing head ride along
                animation_segment=[
                    Operation(target="curve", op=OperationType.CREATE,
                              run_time=6.0, rate_func=RateFunction.LINEAR),
                    Operation(target="head", op=OperationType.FADE_IN,
                              run_time=0.5, with_previous=True),
                ],
                narration=NarrationSegment(
                    text="The path never repeats, yet never escapes — it winds "
                         "forever onto these two wings."),
                hold_seconds=2.0,
                ambient=[AmbientAnimation(type=AmbientType.CAMERA_DRIFT,
                                          amplitude=0.05, period=8.0)],
            ),
        ],
    )

    return LectureIR(
        manim_version="0.18.1",
        render=RenderConfig(quality=Quality.PRODUCTION, fps=60,
                            resolution=(2560, 1440)),
        lecture=Lecture(
            topic="The Lorenz attractor",
            subject=Subject.MATH,
            assumptions=["You've seen a differential equation before."],
            objectives=["See deterministic chaos as a shape."],
            opener="A weather model, too simple to be real, that changed how we "
                   "think about prediction.",
            learning_outcomes=["Recognise a strange attractor when you see one."],
        ),
        storyboard=Storyboard(
            goal="Show the Lorenz attractor as an object",
            steps=[
                StoryboardStep(move=StoryboardMove.HOOK,
                               goal="Equations, then motion", scene_id="s_lorenz"),
            ],
        ),
        scenes=[scene],
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
    euler = build_euler()
    print("VALID Euler lecture built.")
    print(f"  scenes: {len(euler.scenes)}  total ~ {euler.duration_seconds}s")

    lorenz = build_lorenz()
    print("VALID Lorenz lecture built.")
    print(f"  scenes: {len(lorenz.scenes)}  total ~ {lorenz.duration_seconds}s")
    print(f"  render: {lorenz.render.quality.value} @ {lorenz.render.fps}fps "
          f"{lorenz.render.resolution}")

    print("\nNegative tests (each SHOULD be rejected):")

    # -- original guards still hold --
    expect_failure("op before create", lambda: Scene(
        id="bad1", class_name="Bad1",
        scene_graph=[SceneObject(id="c", entity_type=EntityType.CIRCLE)],
        beats=[Beat(animation_segment=[
            Operation(target="c", op=OperationType.MOVE)])],
    ))

    expect_failure("2 equations in a beat", lambda: Scene(
        id="bad2", class_name="Bad2",
        scene_graph=[
            SceneObject(id="e1", entity_type=EntityType.MATH_TEX),
            SceneObject(id="e2", entity_type=EntityType.MATH_TEX),
        ],
        beats=[Beat(animation_segment=[
            Operation(target="e1", op=OperationType.WRITE),
            Operation(target="e2", op=OperationType.WRITE)])],
    ))

    expect_failure("off-frame position", lambda: Position(x=99, y=0))

    expect_failure("dangling storyboard ref", lambda: LectureIR(
        lecture=Lecture(topic="x", subject=Subject.CS),
        storyboard=Storyboard(goal="g", steps=[
            StoryboardStep(move=StoryboardMove.INTRODUCE, goal="g",
                           scene_id="ghost")]),
        scenes=[],
    ))

    # -- new v2 guards --

    # 5. 3D scene that begins in 2D but never pans into orientation
    expect_failure("3D never pans in", lambda: Scene(
        id="bad_3d", class_name="Bad3D", is_3d=True, begin_in_2d=True,
        camera=Camera(is_3d=True),
        scene_graph=[SceneObject(id="s", entity_type=EntityType.SPHERE)],
        beats=[Beat(animation_segment=[
            Operation(target="s", op=OperationType.CREATE)])],
    ))

    # 6. fix_in_frame requested in a 2D scene
    expect_failure("fix_in_frame in 2D", lambda: Scene(
        id="bad_fix", class_name="BadFix",
        scene_graph=[SceneObject(id="t", entity_type=EntityType.MATH_TEX,
                                 fix_in_frame=True)],
    ))

    # 7. behavior tracks a path that doesn't exist
    expect_failure("endpoint tracks ghost", lambda: Scene(
        id="bad_beh", class_name="BadBeh",
        scene_graph=[SceneObject(id="d", entity_type=EntityType.DOT,
                                 behaviors=[Behavior(
                                     type=BehaviorType.TRACK_ENDPOINT,
                                     of="ghost_curve")])],
    ))

    # 8. object references an unknown computation
    expect_failure("unknown computation", lambda: Scene(
        id="bad_comp", class_name="BadComp",
        scene_graph=[SceneObject(id="c", entity_type=EntityType.PARAMETRIC_CURVE,
                                 computation="nope")],
    ))

    # 9. TransformFromCopy with no source
    expect_failure("copy without source", lambda: Operation(
        target="x", op=OperationType.TRANSFORM_FROM_COPY))

    # 10. camera op targeting a normal object
    expect_failure("camera op on object", lambda: Operation(
        target="circle", op=OperationType.MOVE_CAMERA))

    # 11. non-camera op targeting the reserved camera id
    expect_failure("object op on camera", lambda: Operation(
        target=CAMERA_TARGET, op=OperationType.MOVE))

    # 12. bad class name (not a valid identifier / not PascalCase)
    expect_failure("lowercase class_name", lambda: Scene(
        id="bad_cls", class_name="notAClass"))

    # 13. wiki source without a query
    expect_failure("wiki without query", lambda: SceneObject(
        id="w", entity_type=EntityType.MATH_TEX,
        symbol_source=SymbolSource.WIKIDATA))

    # 14. stricter policy via validation context
    print("\nStricter policy via context (max_new_objects_per_beat=1):")
    strict = CognitiveLoadPolicy(max_new_objects_per_beat=1)
    expect_failure("2 objects under strict policy", lambda: Scene.model_validate(
        {
            "id": "strict", "class_name": "Strict",
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