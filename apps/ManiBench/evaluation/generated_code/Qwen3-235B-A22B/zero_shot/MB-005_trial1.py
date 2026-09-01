from manim import *

class DeterminantAnimation(LinearTransformationScene):
    def __init__(self):
        super().__init__(
            i_hat_color=BLUE,
            j_hat游戏副本=RED,
            show_coordinates=True
        )

    def construct(self):
        # Define the matrix A
        matrix = [[2, 1], [0.5, 1.5]]
        matrix_mob = Matrix(matrix).to_corner(UL).scale(0.8)
        matrix_label = Tex("A = ").next_to(matrix_mob, LEFT).scale(0.8)
        
        # Create labels
        original_area_label = Tex("Original Area = 1").to_corner(UR).scale(0.7)
        self.add(original_area_label)
        
        # Display matrix
        self.add_matrix(matrix_mob)
        self.play(Write(matrix_label))
        
        # Create unit square (parallelogram formed by i and j hat)
        unit_parallelogram = self.get_vector_diagram(
            vectors=[np.array([1,0,0]), np.array([0,1,0])],
            vector_config=[{"color": BLUE}, {"color": RED}]
        )
        unit_shape = Polygon(
            ORIGIN, RIGHT, RIGHT + UP, UP, 
            color=YELLOW, fill_opacity=0.3, stroke_width=2
        )
        self.add(unit_shape)
        
        # Add determinant value display
        det_value = abs(matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0])
        det_label = DecimalNumber(det_value, num_decimal_places=2)
        det_text = VGroup(Tex("New Area = |det(A)| = "), det_label).arrange(RIGHT).to_corner(DR).scale(0.7)
        self.add(det_text)
        
        # Animate transformation
        self.play(
            self.apply_matrix(matrix),
            UpdateFromFunc(det_label, lambda d: d.set_value(
                abs(self.moving_mobjects[0].get_vector()[0] * self.moving_mobjects[1].get_vector()[1] - 
                    self.moving_mobjects[0].get_vector()[1] * self.moving_mobjects[1].get_vector()[0])
            )),
            run_time=3
        )
        
        # Update area label
        new_area_label = Tex(f"New Area = |det(A)| = {det_value:.2f}").to_corner(UR).scale(0.7)
        self.play(Transform(original_area_label, new_area_label))
        
        self.wait()


    def get_vector_diagram(self, vectors, vector_config):
        diagram = VGroup()
        for i, vec in enumerate(vectors):
            vector = Vector(vec[:2], **vector_config[i])
            diagram.add(vector)
        return diagram