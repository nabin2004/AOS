import re
import time
from typing import List
from queue import Queue
from pydantic_ai import Agent

from apps.educlaw.streaming_engine.models import SlideData

# A simple mock agent for demonstration purposes,
# In reality, this would use the configured Qwen/Gemma model via Pydantic AI
# from apps.agents.ollama_model import OllamaModel etc.

class LectureProducer:
    def __init__(self, queue: Queue):
        self.queue = queue
        
    def generate_syllabus(self, prompt: str) -> List[str]:
        # Mock syllabus generation
        return [
            "Introduction to the concept",
            "The core mechanism",
            "Conclusion"
        ]
        
    def run_production_loop(self, syllabus: List[str]):
        """Background thread to generate slides based on syllabus."""
        for i, topic in enumerate(syllabus):
            # Simulate LLM inference delay
            time.sleep(2) 
            
            is_final = (i == len(syllabus) - 1)
            
            # Mock LLM generation of the markdown
            markdown_content = f"""
Here is the slide content:
<narration>
Welcome. Today we will cover {topic}. <bookmark mark="v1"/> As you can see...
</narration>

```python
slide_text = Text("{topic}").scale(1.5)
self.wait_until_bookmark("v1")
self.play(Write(slide_text))
```
            """
            
            slide_data = self._parse_markdown(markdown_content)
            slide_data.is_final_slide = is_final
            self.queue.put(slide_data)
            
    def _parse_markdown(self, markdown: str) -> SlideData:
        narration_match = re.search(r'<narration>(.*?)</narration>', markdown, re.DOTALL)
        python_match = re.search(r'```python(.*?)```', markdown, re.DOTALL)
        
        narration = narration_match.group(1).strip() if narration_match else ""
        python_code = python_match.group(1).strip() if python_match else ""
        
        return SlideData(narration=narration, python_code=python_code)
