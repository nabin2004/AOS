import { tool } from "@opencode-ai/plugin"
import path from "path"

/**
 * OpenCode → AOS bridge.
 *
 * Invokes the existing PydanticAI animate pipeline (Manim + voiceover → MP4).
 * Does not reimplement agent logic in TypeScript.
 */
export default tool({
  description: `
Generate an educational animation using the AOS PydanticAI pipeline.
The pipeline classifies the topic, plans a lecture, writes Manim VoiceoverScene
code, renders video, synthesizes in-scene narration, and returns a final MP4
with an audio stream.

Use this whenever the user asks for a Manim / educational animation / explainer video.
`,
  args: {
    prompt: tool.schema
      .string()
      .describe("What the animation should teach (topic + any style/duration hints)"),
    output_dir: tool.schema
      .string()
      .optional()
      .describe("Optional directory to copy final.mp4 and scene source into"),
  },
  async execute(args, context) {
    const repoRoot = context.worktree || context.directory
    const cli = path.join(repoRoot, "apps", "agents", "cli.py")
    const agentsDir = path.join(repoRoot, "apps", "agents")

    const cmd = ["uv", "run", "python", cli, "animate", args.prompt, "--json", "--no-banner"]
    if (args.output_dir) {
      cmd.push("--output-dir", args.output_dir)
    }

    const proc = Bun.spawn(cmd, {
      cwd: agentsDir,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ...process.env,
        // Prefer local Ollama for the inner coder unless the user overrides.
        AOS_MODEL_PROFILE: process.env.AOS_MODEL_PROFILE || "local",
        AOS_CODER_MODEL:
          process.env.AOS_CODER_MODEL || "ollama:qwen2.5-coder:7b",
      },
    })

    const stdout = await new Response(proc.stdout).text()
    const stderr = await new Response(proc.stderr).text()
    const code = await proc.exited

    let artifact: Record<string, unknown> | null = null
    const line = stdout.trim().split(/\r?\n/).filter(Boolean).pop()
    if (line) {
      try {
        artifact = JSON.parse(line)
      } catch {
        artifact = null
      }
    }

    if (!artifact) {
      return [
        "AOS animate failed: could not parse JSON result.",
        `exit_code=${code}`,
        stderr ? `stderr:\n${stderr.slice(-4000)}` : "",
        stdout ? `stdout:\n${stdout.slice(-2000)}` : "",
      ]
        .filter(Boolean)
        .join("\n")
    }

    const ok = Boolean(artifact.ok)
    const video = artifact.video_path || "—"
    const scene = artifact.scene_path || artifact.scene_file || "—"
    const runDir = artifact.run_dir || "—"
    const hasAudio = artifact.has_audio
    const traj = artifact.trajectory_path || "—"
    const err = artifact.error || ""

    if (!ok) {
      return [
        "Animation generation failed.",
        `error: ${err || "unknown"}`,
        `run_dir: ${runDir}`,
        `has_audio: ${hasAudio}`,
        `trajectory: ${traj}`,
        stderr ? `stderr (tail):\n${stderr.slice(-2000)}` : "",
      ]
        .filter(Boolean)
        .join("\n")
    }

    return [
      "Animation generated successfully.",
      `Video: ${video}`,
      `Manim source: ${scene}`,
      `Run dir: ${runDir}`,
      `has_audio: ${hasAudio}`,
      `Trajectory: ${traj}`,
    ].join("\n")
  },
})
