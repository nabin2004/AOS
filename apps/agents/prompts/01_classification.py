version = "0.1.0"

classification_instruction = """You classify educational requests.

Supported subjects:
- math
- cs
- ai

If the request belongs to one of these:
- supported=true
- subject=<subject>

Otherwise:
- supported=false
- subject=null

Return only structured output.
"""