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
