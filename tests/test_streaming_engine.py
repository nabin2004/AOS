import pytest
from apps.educlaw.streaming_engine.producer import LectureProducer
from queue import Queue

def test_markdown_extraction():
    q = Queue()
    producer = LectureProducer(q)
    
    mock_markdown = """
Here is the slide:
<narration>
Hello world. <bookmark mark="v1"/> Watch this!
</narration>

Some text in between.

```python
self.play(Write(Text("Hello")))
```
    """
    
    slide_data = producer._parse_markdown(mock_markdown)
    
    assert "Hello world." in slide_data.narration
    assert "Watch this!" in slide_data.narration
    assert "self.play(Write(Text(\"Hello\")))" in slide_data.python_code


def test_slide_data_model():
    from apps.educlaw.streaming_engine.models import SlideData

    s = SlideData(1, "Narration text", "self.play()", is_final=True)
    assert s.slide_num == 1
    assert s.narration == "Narration text"
    assert s.python_code == "self.play()"
    assert s.is_final is True
    assert s.is_final_slide is True


def test_streaming_api_app_routes():
    from apps.educlaw.streaming_engine.api import app, router

    router_paths = [getattr(r, "path", None) for r in router.routes]
    assert "/ws/generate_lecture" in router_paths
