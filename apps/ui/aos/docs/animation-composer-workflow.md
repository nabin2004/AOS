# Animation Composer workflow

## Intent

Chat is the default experience. Animation is a deliberate, message-scoped next action:

```text
user prompt -> assistant explanation -> Animate this explanation -> Composer
                                                        |
                                                        v
                                      plan -> code -> render -> review / repair
```

This keeps the expensive Manim workflow out of ordinary conversation while preserving the exact explanation the user chose to animate.

## Frontend entry point

`frontend/src/components/chat/message-item.tsx` renders **Animate this explanation** only for a completed assistant response that looks animatable. The click creates an `AnimationSession` with:

- `conversationId`
- `sourceMessageId` (the assistant response selected by the user)
- `sourcePrompt` (the preceding user prompt, when present)
- `sourceText` (the explanation to animate)

Do not replace this action with a chat message such as `Animate this`. The source message ID is the stable semantic link needed to recover conversation context, files, knowledge-base citations, and model configuration later.

## State model

`frontend/src/stores/animation-session-store.ts` owns the active UI session. Its four public stages are:

| Stage | Purpose |
| --- | --- |
| `composer` | User selects the animation emphasis and supplies instructions. |
| `coding` | The Coder Agent synthesizes or patches Manim CE code. |
| `rendering` | Code is compiled and rendered. |
| `review` | The user accepts the video or submits a repair request. |

The store is intentionally not persisted: an animation run is an active workflow, not a chat preference. Persist it only after the backend provides durable animation-session records.

## Composer customization

`manim-studio-modal.tsx` is the Composer surface. The available emphasis values are `concept`, `geometric`, `derivation`, and `ai`. To add an option:

1. Add it to `AnimationEmphasis`.
2. Add its button in the Composer options.
3. Add its instruction in `handleCreatePlan`.
4. If the server adopts a structured request, add the corresponding field to the backend schema and prompt template.

Composer currently combines the source question, source explanation, selected emphasis, and optional instructions into the existing `/api/videos/plan` request. This keeps the change compatible with the current plan/code/render endpoints while providing a clean place to move to a structured server-side session.

## Pipeline and repair behavior

The plan endpoint produces `scenes.md`; the code endpoint receives that plan and produces a Manim Community scene. Review feedback follows the narrow repair loop:

```text
review issue -> repair directive -> Coder Agent -> render -> review
```

Do not restart Composer for visual problems such as overlapping labels. Reuse the current plan and code context, and patch the code. A new Composer pass is appropriate only when the instructional goal changes.

When extending generated Manim code, retain the project conventions: use Manim Community imports, group and position mobjects deliberately, use `MathTex` for formulae, and render previews at `-ql` before higher qualities.

## Durable backend and WebSocket evolution

The UI currently uses the existing REST plan/code/render endpoints. The next backend iteration should create an animation-session resource from `conversation_id` and `source_message_id`, retrieving source text server-side rather than trusting a browser copy.

Add these event types to the shared WebSocket contract when that session API is introduced:

```text
animation_session_created
animation_stage_changed
composer_plan_updated
code_generated
render_started
render_progress
render_completed
review_result
repair_started
repair_completed
```

`useChat` should route those events to `useAnimationSessionStore`; ordinary text and tool events must remain in `useChatStore`. This separation keeps chat history stable while Composer updates in real time.

## Testing checklist

- A normal response has no studio chrome until its message action is clicked.
- Composer displays the selected response and its source question.
- Changing emphasis changes the plan request context.
- Code, render, and critique keep the same session/source IDs.
- A repair returns to code and render, not to Composer.
- Existing one-shot modes remain available only as advanced alternatives; the everyday Animate entry point is the message action.
