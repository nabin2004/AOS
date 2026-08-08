import type { ChatMessage, ToolCall } from "@/types";

export interface VideoGenerationDto {
  id: string;
  conversation_id: string;
  prompt: string;
  mode: string;
  status: string;
  minio_key?: string | null;
  error_message?: string | null;
  assistant_message_id?: string | null;
}

/** Apply a video generation row to the matching generate_video tool part. */
export function applyVideoStatusToMessage(
  msg: ChatMessage,
  video: VideoGenerationDto,
): ChatMessage {
  const toolCallId = `generate_video_${video.id}`;
  const resultPayload = {
    kind: "video" as const,
    video_generation_id: video.id,
    mode: video.mode,
    prompt: video.prompt,
    status: video.status,
    minio_key: video.minio_key,
    error: video.error_message,
    message:
      video.status === "completed"
        ? "Your video is ready."
        : video.status === "failed"
          ? `Video generation failed: ${video.error_message || "unknown error"}`
          : video.status === "running"
            ? "Generating video…"
            : "Queued… preparing animation pipeline.",
  };
  const toolStatus: ToolCall["status"] =
    video.status === "completed"
      ? "completed"
      : video.status === "failed"
        ? "error"
        : "running";

  const patchTool = (tc: ToolCall): ToolCall =>
    tc.id === toolCallId || tc.name === "generate_video"
      ? {
          ...tc,
          id: toolCallId,
          status: toolStatus,
          result: JSON.stringify(resultPayload),
          args: {
            ...tc.args,
            mode: video.mode,
            video_generation_id: video.id,
            prompt: video.prompt,
          },
        }
      : tc;

  return {
    ...msg,
    toolCalls: msg.toolCalls?.map(patchTool),
    parts: msg.parts?.map((p) =>
      p.type === "tool" && p.toolCall
        ? { ...p, toolCall: patchTool(p.toolCall) }
        : p,
    ),
    isStreaming: video.status === "pending" || video.status === "running",
  };
}

/** Build a synthetic assistant bubble when a video row has no matching message. */
export function videoGenerationToChatMessage(video: VideoGenerationDto): ChatMessage {
  const toolCallId = `generate_video_${video.id}`;
  const resultPayload = {
    kind: "video" as const,
    video_generation_id: video.id,
    mode: video.mode,
    prompt: video.prompt,
    status: video.status,
    minio_key: video.minio_key,
    error: video.error_message,
    message:
      video.status === "completed"
        ? "Your video is ready."
        : video.status === "failed"
          ? `Video generation failed: ${video.error_message || "unknown error"}`
          : video.status === "running"
            ? "Generating video…"
            : "Queued… preparing animation pipeline.",
  };
  const toolStatus: ToolCall["status"] =
    video.status === "completed"
      ? "completed"
      : video.status === "failed"
        ? "error"
        : "running";

  const toolCall: ToolCall = {
    id: toolCallId,
    name: "generate_video",
    args: {
      mode: video.mode,
      video_generation_id: video.id,
      prompt: video.prompt,
    },
    status: toolStatus,
    result: JSON.stringify(resultPayload),
  };

  const content =
    video.status === "completed"
      ? "Your video is ready."
      : video.status === "failed"
        ? `Video generation failed: ${video.error_message || "unknown error"}`
        : `Starting ${video.mode} video generation…`;

  return {
    id: video.assistant_message_id || `video-pending-${video.id}`,
    role: "assistant",
    content,
    timestamp: new Date(),
    conversationId: video.conversation_id,
    toolCalls: [toolCall],
    parts: [
      { id: toolCallId, type: "tool", toolCall },
      { id: `${video.id}-text`, type: "text", content },
    ],
    isStreaming: video.status === "pending" || video.status === "running",
  };
}
