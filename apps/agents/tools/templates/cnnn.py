from manim import *

class CNNN(Scene):
    def construct(self):
        title = Title("Convolution Neural Network")
        self.play(Create(title))

        self.wait(2)        
        self.play(FadeOut(title))

        self.wait(2)        
        my_matrix = Matrix([[1, 2], [3, 4]])
        my_matrix.to_corner(UP + LEFT)
        # print(my_matrix[1])
        # self.add(Tex(my_matrix[1]))



        
        # Add to scene and play animation
        self.play(Create(my_matrix))

        my_matrix2 = Matrix([[5, 6], [7, 8]])
        my_matrix2.next_to(my_matrix)
        self.play(Create(my_matrix2))

        text = Tex("This our image")
        text.next_to(my_matrix2, RIGHT)

        self.play(Create(text))

        self.wait()

