---
name: manim-render
description: >-
  Use this skill when rendering Manim scenes, managing Docker render containers, or troubleshooting Manim execution and ffmpeg assembly.
---

# Manim Rendering & Assembly

This skill details rendering Manim animations in Docker and assembling final video outputs.

## Common Operations

### 1. Rendering a Single Manim Scene
To render a scene file manually using Docker:
```bash
docker run --rm -v ${PWD}:/manim manimcommunity/manim manim -ql scene.py SceneClassName
```

### 2. Cleaning Up Persistent Render Containers
When runs finish or containers become orphaned:
```bash
# On Linux/macOS
docker ps --filter "name=aos-manim-" -q | xargs -r docker rm -f

# On Windows PowerShell
docker ps --filter "name=aos-manim-" -q | ForEach-Object { docker rm -f $_ }
```

### 3. Assembling Video & Narration Audio with FFmpeg
If stitching video with beat audio manually:
```bash
ffmpeg -y -i scene_video.mp4 -i scene_audio.wav -c:v copy -c:a aac -shortest output_scene.mp4
```

### 4. Troubleshooting Common Issues
- **Missing LaTeX packages**: For complex formulas, ensure formula strings in `SceneObject.content` are standard mathematical notation without unusual custom LaTeX packages.
- **Docker Mount Issues**: Verify Docker Desktop file sharing permissions for the repository path.
