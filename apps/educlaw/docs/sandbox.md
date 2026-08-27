# Sandbox

EduClaw never runs bash on the host. File writes stay in the workspace jail; shell and Manim run in **`manimcommunity/manim`**.

## Docker

```text
docker run --rm -v "<cwd>:/manim" -w /manim manimcommunity/manim manim -qm scene.py SceneName
```

| Env | Default |
|-----|---------|
| `EDUCLAW_MANIM_IMAGE` | `manimcommunity/manim:stable` |
| `EDUCLAW_DOCKER_USER` | unset (`uid:gid` on Linux if the mount owner is wrong) |
| `EDUCLAW_MANIM_QUALITY` | `m` (`l` / `m` / `h` / `k`) |

Preview flags `-p` and `-f` are not supported in the container. The image has a minimal TeX Live; see the `manim-latex` skill for `ctex`.

## Tools

| Tool | Action |
|------|--------|
| `sandbox_read` | Read a jailed path |
| `sandbox_write` | Write, then run syntax/`ty` on `.py` |
| `sandbox_bash` | `docker run … bash -lc` |
| `manim_render` | `manim -q{l\|m\|h\|k} file.py Scene` |

If Docker is missing, tools return an error string. Tests cover argv construction only.
