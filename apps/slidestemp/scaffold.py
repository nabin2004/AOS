import os

def main():
    print("=========================================")
    print("      AOS Video Scaffold Generator       ")
    print("=========================================")
    
    filename = input("Enter output filename (e.g. neural_network.py): ").strip()
    if not filename.endswith('.py'):
        filename += '.py'

    lecture_num = input("Enter Lecture Number (e.g. 1): ").strip()
    title = input("Enter Main Title (e.g. Backpropagation): ").strip()
    subtitle = input("Enter Subtitle (e.g. Teaching a Neural Network to Learn): ").strip()

    print("\nWhich components do you want to include in this video?")
    inc_branding = input("- Branding Intro? (y/n): ").strip().lower() == 'y'
    inc_slide = input("- Basic Slide? (y/n): ").strip().lower() == 'y'
    inc_quote = input("- Quote? (y/n): ").strip().lower() == 'y'
    inc_arch = input("- Architecture Explaining? (y/n): ").strip().lower() == 'y'
    inc_code = input("- Code Walkthrough? (y/n): ").strip().lower() == 'y'

    content = f"""from manim import *
try:
    from theme import *
except ImportError:
    pass

lecture_number = "{lecture_num}"
nameOfTitle = "{title}"
subtitle = "{subtitle}"
COLOR_NAME = WHITE

class MainVideo(Scene):
    def construct(self):
"""
    
    if inc_branding:
        content += """
        # --- 1. Branding Intro ---
        self.add_sound("audio/brand_music.mp3")
        brand = Text("RUKUMINI", font_size=70, color=BLUE)
        self.play(Write(brand))
        self.wait(1)
        box = SurroundingRectangle(brand, color=WHITE, buff=MED_SMALL_BUFF)
        _N_letter = brand.copy()
        nabin = Text("by Nabin", font_size=30)
        nabin.move_to(DOWN * 0.9)
        self.play(Transform(_N_letter[6][0], nabin))
        self.play(Write(box))
        self.wait(2)

        self.play(Unwrite(brand))
        self.wait(1)

        lec_title = Title(f"Lecture {lecture_number}")
        self.play(Transform(box[0], lec_title))

        lecture_no_text = Text(f"{nameOfTitle}", font_size=50, color=BLUE)
        sub_text = Text(subtitle, font_size=30)
        sub_text.move_to(DOWN * 0.8)
        self.play(Write(lecture_no_text), Transform(_N_letter[6], sub_text))
        self.wait(1)
        self.clear()
        self.wait(1)
"""

    if inc_slide:
        content += """
        # --- 2. Basic Slide ---
        slide_title = Text("Click to add title", font_size=50, color=BLUE)
        slide_subtitle = Text("Click to add subtitle", font_size=30).move_to(DOWN)
        self.play(Write(slide_title, run_time=1.5))
        self.play(FadeIn(slide_subtitle))
        self.wait(2)
        self.clear()
"""

    if inc_quote:
        content += """
        # --- 3. Quote ---
        quote = Text(
            "Study what interests you\\nin the most undisciplined,\\nirreverent and original manner possible.",
            font="CMU Serif", font_size=52, line_spacing=0.8
        )
        author = Text("— Richard Feynman", font="CMU Serif", font_size=30, color=GREY_B, slant=ITALIC)
        author.next_to(quote, DOWN, buff=0.7).align_to(quote, RIGHT)
        self.play(Write(quote), run_time=3)
        self.play(FadeIn(author, shift=0.2 * UP))
        self.wait(3)
        self.clear()
"""

    if inc_arch:
        content += """
        # --- 4. Architecture Explaining ---
        arch_title = Title("Transformer Encoder")
        bullets = BulletedList("Multi-Head Attention", "Add & LayerNorm", "MLP", font_size=34)
        bullets.to_edge(LEFT).next_to(arch_title, DOWN)
        self.play(Write(arch_title))
        self.play(FadeIn(bullets))
        self.wait(2)
        self.clear()
"""
    
    if inc_code:
        content += """
        # --- 5. Code Walkthrough ---
        # Note: Ensure the file 'codess/helloworld.py' exists relative to where you run Manim
        try:
            listing = Code(
                "codess/helloworld.py",
                tab_width=4,
                formatter_style="vs",
                language="python",
            )
            self.play(Create(listing))
            self.wait(2)
        except Exception as e:
            print(f"Failed to load code file: {e}")
        self.clear()
"""

    if not any([inc_branding, inc_slide, inc_quote, inc_arch, inc_code]):
        content += """        pass\n"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n[SUCCESS] Scaffold created at: {filename}")
    print(f"You can now render it using:")
    print(f"    manim -pqh {filename} MainVideo")

if __name__ == "__main__":
    main()
