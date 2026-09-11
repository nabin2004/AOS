import os
import queue
import time
import numpy as np
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class EduClawStreamingScene(VoiceoverScene):
    def construct(self):
        # We assume self.slide_queue is passed or set before construct
        # For this prototype, we'll access it via a global or class attribute
        # However, a cleaner way is passing it via scene config. 
        # Since Manim instantiates this, we can rely on a singleton or registry.
        import apps.educlaw.streaming_engine.api as api_registry
        
        self.slide_queue = api_registry.active_queue
        
        self.set_speech_service(GTTSService())
        self.play_branding_intro()
        
        slide_number = 1
        
        while True:
            try:
                slide_data = self.slide_queue.get(timeout=0)
                self.remove_tv_static()
                
                narration_text = slide_data.narration
                python_script = slide_data.python_code
                
                if not python_script:
                    python_script = "self.wait(1)" # fallback
                    
                with self.voiceover(text=narration_text) as tracker:
                    exec_locals = {
                        "self": self,
                        "np": np,
                        "tracker": tracker,
                        "MathTex": MathTex,
                        "Text": Text,
                        "Write": Write,
                        "Create": Create,
                        "FadeIn": FadeIn,
                        "Transform": Transform,
                        "VGroup": VGroup,
                        "UP": UP,
                        "DOWN": DOWN,
                        "LEFT": LEFT,
                        "RIGHT": RIGHT,
                        "BLUE": BLUE,
                        "RED": RED,
                    }
                    try:
                        exec(python_script, globals(), exec_locals)
                    except Exception as e:
                        print(f"Error executing LLM code: {e}")
                        self.wait(2) # fallback wait
                        
                slide_number += 1
                
                if slide_data.is_final_slide:
                    break
                    
            except queue.Empty:
                self.show_tv_static()
                time.sleep(0.5)

    def play_branding_intro(self):
        """Phase 2: Compute Buffer Intro.
        
        Plays establishing branding using college and project assets from
        apps/agents/tools/assets/ to buy 10-15s of compute time for LLM Slide 1.
        """
        assets_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "agents", "tools", "assets")
        )
        rukumini_logo_path = os.path.join(assets_dir, "rukumini.png")
        college_logo_path = os.path.join(assets_dir, "college_logo.png")

        # Fallback to Text if assets not found
        if os.path.exists(rukumini_logo_path):
            logo = ImageMobject(rukumini_logo_path).scale(0.8)
        else:
            logo = Text("RUKUMINI", font_size=56, weight=BOLD, color="#C41E3A")

        subtext = Text("Agentic Educational Orchestration System", font_size=24, color=GRAY)
        subtext.next_to(logo, DOWN, buff=0.4)

        self.play(FadeIn(logo, shift=UP * 0.5), FadeIn(subtext), run_time=1.5)
        self.wait(1.5)

        if os.path.exists(college_logo_path):
            college_logo = ImageMobject(college_logo_path).scale(0.5).to_corner(DR, buff=0.6)
            self.play(FadeIn(college_logo, shift=LEFT * 0.3), run_time=1.0)
            self.wait(1.0)
            self.play(FadeOut(logo), FadeOut(subtext), FadeOut(college_logo), run_time=1.0)
        else:
            self.play(FadeOut(logo), FadeOut(subtext), run_time=1.0)

    def show_tv_static(self):
        """Phase 5: Buffer Underrun Graceful Degradation.
        
        Uses ImageMobject-based CRT noise with scanlines, flicker, and vignette
        from tv_static.py to keep rendering smooth while LLM catches up.
        """
        if not hasattr(self, 'tv_static_active') or not self.tv_static_active:
            tex_w, tex_h = 192, 108  # 16:9 texture scaled to viewport

            def random_frame():
                # Uniform random grayscale noise (h, w), uint8, contrast-boosted
                noise = np.random.randint(0, 255, (tex_h, tex_w), dtype=np.uint8).astype(np.float32)
                noise = (noise - 127.5) * 1.5 + 127.5
                gray = np.clip(noise, 25, 255)

                # CRT scanlines: darken every alternate row
                gray[::2, :] *= 0.5

                # Glitch band: occasional vertical-sync roll
                if np.random.random() < 0.15:
                    row = np.random.randint(0, tex_h)
                    band = slice(row, min(row + 2, tex_h))
                    gray[band, :] = 255

                # Global frame flicker
                flicker = np.random.uniform(0.75, 1.0)
                gray = np.clip(gray * flicker, 0, 255).astype(np.uint8)

                # Broadcast to 3 channels so R == G == B (authentic monochrome snow)
                return np.stack([gray, gray, gray], axis=-1)

            # Create fullframe ImageMobject
            init_frame = random_frame()
            self.static_mob = ImageMobject(init_frame)
            self.static_mob.width = config.frame_width
            self.static_mob.height = config.frame_height

            def update_static(mob: ImageMobject, dt: float) -> None:
                mob.pixel_array[:, :, :3] = random_frame()
                mob.pixel_array = mob.pixel_array  # Texture cache bust

            self.static_mob.add_updater(update_static)

            self.static_vignette = Rectangle(
                width=config.frame_width,
                height=config.frame_height,
                fill_color=BLACK,
                fill_opacity=0.35,
                stroke_width=0,
            )
            self.static_vignette.set_z_index(10)
            self.static_mob.set_z_index(9)

            self.static_label = Text("... BUFFERING NEXT SLIDE ...", font_size=28, color=RED, weight=BOLD)
            self.static_label.set_z_index(11)

            self.add(self.static_mob, self.static_vignette, self.static_label)
            self.tv_static_active = True

    def remove_tv_static(self):
        if hasattr(self, 'tv_static_active') and self.tv_static_active:
            if hasattr(self, 'static_mob'):
                self.static_mob.clear_updaters()
                self.remove(self.static_mob, self.static_vignette, self.static_label)
            self.tv_static_active = False
