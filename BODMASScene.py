from manim import *

class BODMASScene(Scene):
    def construct(self):
        # Title
        title = Text("BODMAS Rule")
        title.to_edge(UP)
        
        # Display the expression
        expression = Tex("5 + (6 \\times 2) - 3^2 \\div 3")
        expression.next_to(title, DOWN)
        
        self.play(Write(title), Write(expression))
        self.wait(1)

        # Step 1: Solve Brackets
        brackets_result = Tex("= 5 + 12 - 3^2 \\div 3")
        self.play(Transform(expression, brackets_result))
        self.wait(1)

        # Step 2: Solve Orders
        orders_result = Tex("= 5 + 12 - 9 \\div 3")
        self.play(Transform(expression, orders_result))
        self.wait(1)

        # Step 3: Solve Division
        division_result = Tex("= 5 + 12 - 3")
        self.play(Transform(expression, division_result))
        self.wait(1)

        # Step 4: Solve Addition and Subtraction
        final_result = Tex("= 14")
        self.play(Transform(expression, final_result))
        self.wait(1)

        # End scene
        self.play(FadeOut(expression), FadeOut(title))
