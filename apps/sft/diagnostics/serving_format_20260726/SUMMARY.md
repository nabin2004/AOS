# Serving-format diagnosis summary

## Template audit
- templates_identical: True
- modelfile_has_TEMPLATE: True
- distinctive_only_sft: []
- ollama markers: {'tool_call_call': True, 'tool_call_end': True, 'pipe_string': True, 'turn': True, 'channel_thought': True, 'think': True, 'generation_marker': True, 'enable_thinking': True}
- sft markers: {'tool_call_call': True, 'tool_call_end': True, 'pipe_string': True, 'turn': True, 'channel_thought': True, 'think': True, 'generation_marker': True, 'enable_thinking': True}

## Jinja golden
{
  "rendered_len": 845,
  "tool_surface_preview": "<|tool_call>call:run_code{code:<|\"|>code = '''from manim import *\\nclass Demo(Scene):\\n    def construct(self):\\n        self.play(Create(Circle()))'''\nawait manim_write(code=code, scene_name='Demo')<|\"|>}<tool_call|><|tool_response>",
  "has_tool_call_markup": true,
  "has_pipe_string": true
}

## Euler hybrid trace
- {'msg': 1, 'kind': 'thinking', 'len': 2119, 'finish_reason': 'tool_call', 'output_tokens': 971, 'tail': ' complexity of synchronizing math with speech.\n\n7.  **Tool Call Generation:** Proceed with `manim_write` and subsequent compilation steps according to the plan. (Using the specified output directory).'}
- {'msg': 1, 'kind': 'tool-call', 'name': 'run_code', 'code_class': 'manim_write_other', 'preflight': {'ok': False, 'error': 'codemode_star_import', 'message': "Do not put `from manim import *` directly in run_code. Nest Manim source inside await manim_write(code='''...''', scene_name='YourScene') or compile_manim_code(...)."}, 'finish_reason': 'tool_call', 'output_tokens': 971}
- {'msg': 2, 'kind': 'retry-prompt', 'preview': 'Type error in code:\nerror[unresolved-import]: Cannot resolve imported module `manim`\n --> main.py:1:6\n  |\n1 | from manim import *\n  |      ^^^^^\n2 | from manim_voiceover import VoiceoverScene\n3 | from'}
- {'msg': 3, 'kind': 'thinking', 'len': 5866, 'finish_reason': 'stop', 'output_tokens': 1245, 'tail': 'n begins, I must generate code based on an assumption. This is highly risky.\n\nI will assume the system intends for me to stop and wait for proper input. No code generation is possible without content.'}
- {'msg': 3, 'kind': 'text', 'content': 'Please provide the lecture plan you would like me to convert into Manim code.', 'finish_reason': 'stop'}

## Probe results
- {"label": "raw_ollama_no_tools_content", "text_len": 2699, "markers": {"has_tool_call_start": false, "has_tool_call_end": false, "has_gemma_string_delim": false, "has_channel_thought": false, "has_think_token": false, "has_turn_marker": false, "has_eos": false, "mentions_run_code": false, "mentions_manim_write": false, "mentions_from_manim": true}, "parse_error": null, "n_gemma_parsed_calls": 0, "leftover_text_preview": "```python\nimport asyncio\nfrom manim import *\n\nasync def visualize_euler
- {"label": "raw_ollama_no_tools_thinking", "thinking_len": 803, "mentions_missing_plan": false, "tail": "scene structure.\n4.  Visualize the unit circle, real axis, imaginary axis, and points corresponding to $e^{ix}$ (which is $e^{i\\theta} = \\cos(\\theta) + i\\sin(\\theta)$).\n\nSince this involves complex numbers and rotation, I'll need to handle the visualization carefully.\n\nLet's start drafting the code."}
- {"label": "raw_openai_with_tools_message_content", "text_len": 0, "markers": {"has_tool_call_start": false, "has_tool_call_end": false, "has_gemma_string_delim": false, "has_channel_thought": false, "has_think_token": false, "has_turn_marker": false, "has_eos": false, "mentions_run_code": false, "mentions_manim_write": false, "mentions_from_manim": false}, "parse_error": null, "n_gemma_parsed_calls": 0, "leftover_text_preview": "", "bodies": []}
- {"label": "raw_openai_with_tools_message_tool_calls", "n_structured_tool_calls": 1, "bodies": [{"name": "run_code", "arg_keys": ["code"], "code_class": "wrap_then_manim_write", "preflight": null, "code_preview": "await manim_write(code=\"\"\"\nfrom manim import *\n\nclass EulersFormulaVisualization(Scene):\n    def construct(self):\n        # Setup the axes and coordinate system\n        axes = Axes(\n            x_range=[-3.5, 3.5, 1],\n            y_range=[-3.5, 3.5, 1],\n            axis_conf
- {"label": "raw_openai_with_tools_message_reasoning", "reasoning_len": 850, "tail": " complex visualization, I will need to use `MathTex` or similar for labels and potentially `Arc` or `Circle` for the circle itself. The core idea is to show how rotating on the unit circle relates to the exponential form.\n\nLet's draft the Manim code."}
- {"label": "raw_openai_full_euler_message_content", "text_len": 0, "markers": {"has_tool_call_start": false, "has_tool_call_end": false, "has_gemma_string_delim": false, "has_channel_thought": false, "has_think_token": false, "has_turn_marker": false, "has_eos": false, "mentions_run_code": false, "mentions_manim_write": false, "mentions_from_manim": false}, "parse_error": null, "n_gemma_parsed_calls": 0, "leftover_text_preview": "", "bodies": []}
- {"label": "raw_openai_full_euler_message_tool_calls", "n_structured_tool_calls": 1, "bodies": [{"name": "run_code", "arg_keys": ["code"], "code_class": "raw_manim_top_level", "preflight": {"ok": false, "error": "codemode_star_import", "message": "Do not put `from manim import *` directly in run_code. Nest Manim source inside await manim_write(code='''...''', scene_name='YourScene') or compile_manim_code(...)."}, "code_preview": "from manim import *\nfrom manim_voiceover import VoiceoverScene\nfr
- {"label": "raw_openai_full_euler_message_reasoning", "reasoning_len": 1299, "tail": "the speech service.\n\n**Step 1: Draft the Manim code.**\nI will focus on creating a visually engaging explanation of the formula's geometric meaning.\n\n**Step 2: Execute and compile.**\nI will use the provided `output_dir`.\n\nLet's start writing the code."}

## Train first-run_code classes
{'rows': 334, 'classes': {'wrap_then_manim_write': 99, 'other_orchestration': 121, 'raw_manim_top_level': 105, 'manim_write_other': 6}}
