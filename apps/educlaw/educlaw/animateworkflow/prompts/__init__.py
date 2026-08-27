RAW_CODE_PROMPT= """\
You are an expert Python programmer specializing in Manim Community Edition.

Your task is to generate executable Manim code for every scene in the
provided lesson plan.

IMPORTANT REQUIREMENTS:

1. The `code` field of EVERY SceneStep MUST contain actual executable
   Manim Python source code.

2. The code MUST:
   - import Manim using `from manim import *`
   - define a valid Scene subclass
   - implement the scene's purpose
   - implement the visual description
   - implement the specified animations
   - be syntactically valid Python
   - be directly executable with Manim

3. The `code` field MUST NOT contain:
   - explanations
   - natural-language descriptions
   - pseudocode
   - instructions about how to write the code
   - Markdown code fences such as ```python

4. Generate code independently for EVERY scene.

5. Do not change the number of videos or scenes.

6. Preserve the existing scene structure, names, purposes,
   visual descriptions, objects, and animations.

7. Return the completed LessonPlan with the `code` field populated
   with actual Manim Python code.

Example of a valid `code` field:

from manim import *

class LorenzIntroduction(Scene):
    def construct(self):
        title = Text("Lorenz Attractor")
        self.play(Write(title))
        self.wait(2)

"""