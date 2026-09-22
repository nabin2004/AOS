# Comprehensive Testing Proposal for AOS (Agentic Orchestration System)

## 1. Objectives

This proposal outlines a robust, production-grade testing strategy for the AOS project. Given the complexity of the multi-agent pipeline, asynchronous task queues, and LLM-driven generations, a multi-layered testing approach is crucial to ensure high quality, reliability, and maintainability. This document serves as a blueprint for implementing comprehensive test cases across the entire stack.

## 2. Core Testing Levels

### 2.1. Unit Testing
- **Goal:** Validate individual, isolated components (functions, classes, agent nodes).
- **Scope:**
  - **Pydantic IR Schemas (`packages/ir`):** Test serialization, deserialization, and field validations (e.g., ensuring `SceneObject.content` logic).
  - **Graph Nodes (`apps/agents/graph.py`):** Mock LLM responses to test the logic within each node (Classify, PlanLecture, MakeStoryboard, etc.) independently.
  - **FastAPI Endpoints (`apps/server`):** Test request/response models, input validation, and basic routing logic.
  - **Audio/Video Tools (`apps/audio_service`, `tools/*`):** Test specific functions (e.g., timestamp alignment logic in `dsm_aligner.py`) with mocked external service calls.
- **Tools:** `pytest`, `unittest.mock`.

### 2.2. Integration Testing
- **Goal:** Verify interactions between different components and subsystems.
- **Scope:**
  - **Agent Pipeline Execution:** Run the `pydantic_graph` with mock LLMs to ensure data flows correctly between nodes (e.g., Output of `PlanLecture` matches the expected input of `MakeStoryboard`).
  - **Database & Storage:** Test the interaction between the FastAPI server and PostgreSQL/Redis/Milvus. Verify Celery workers can correctly pull tasks and update state in Redis.
  - **Docker Rendering Pipeline (`tools/render.py`):** Test the interaction with the Manim Docker container. Send a dummy `lecture.py` and verify successful compilation without relying on the full agent graph.
- **Tools:** `pytest`, `pytest-asyncio`, Testcontainers (for spinning up temporary DB/Redis instances).

### 2.3. End-to-End (E2E) / System Testing
- **Goal:** Validate the entire application flow from the user interface down to the final generated artifact.
- **Scope:**
  - **Automated Pipeline Runs:** Execute the CLI command `uv run python cli.py generate "..."` with a fixed, predictable prompt and a deterministic (or highly controlled) LLM model to verify a final `.mp4` is produced.
  - **Web UI E2E:** Simulate user interactions on the Next.js frontend (submitting a prompt, monitoring progress, viewing the final video).
- **Tools:** Playwright (for Next.js frontend), Bash scripts/Python subprocess for CLI testing.

## 3. Methodologies

### 3.1. White Box Testing
- **Goal:** Test internal structures or workings of the application.
- **Application:**
  - Attaining high code coverage (aiming for >80% on core logic) using `pytest-cov`.
  - Testing internal state transitions within the `pydantic_graph`.
  - Verifying the correct execution paths of the `Validate <-> Repair` loop by intentionally injecting invalid IR schemas and ensuring the repair agent is invoked and successfully resolves the issue.

### 3.2. Black Box Testing
- **Goal:** Test functionality without peeking at internal structures.
- **Application:**
  - API testing: Sending valid/invalid requests to the FastAPI endpoints and checking HTTP status codes and response structures.
  - CLI testing: Providing various inputs to `animus` CLI and verifying expected outputs/errors (e.g., testing behavior when Docker is not running).

### 3.3. User Acceptance Testing (UAT) / Human-in-the-Loop (HITL)
- **Goal:** Ensure the system meets the actual requirements of the end-users (teachers, students).
- **Application:**
  - **Pedagogical Evaluation:** Have educators review generated lectures for accuracy, pacing, and clarity.
  - **Visual & Audio Quality:** Subjective review of the Manim animations and Pocket TTS narration.
  - A/B testing different prompts or models to see which produces better educational outcomes.

## 4. Specialized AI/LLM Testing (Evals)

Testing LLM-based systems requires non-deterministic testing strategies.

### 4.1. Prompt & Output Evals
- **Goal:** Quantify the quality of LLM outputs against specific rubrics.
- **Application:**
  - Create a "Golden Dataset" of prompts and highly-rated expected outputs (e.g., idealized IR schemas).
  - Use an "LLM-as-a-Judge" (e.g., GPT-4) to evaluate the output of the local/smaller models against rubrics (e.g., "Is the math accurate?", "Is the scene sequence logical?").
  - Test the SFT/GRPO/DPO pipelines by evaluating model performance before and after fine-tuning.

### 4.2. Robustness & Security Testing (Red Teaming)
- **Goal:** Ensure the system handles adversarial inputs gracefully.
- **Application:**
  - Prompt Injection Tests: Try to force the LLM to output malicious Manim code or reveal system prompts.
  - Boundary Testing: Input extremely long or complex topics to test system stability and latency.

## 5. Implementation Roadmap

1.  **Phase 1 (Immediate):** Establish the basic `pytest` harness. Write unit tests for `packages/ir` schemas to ensure foundational data structures are solid. Add mock-based tests for `apps/agents/graph.py` nodes.
2.  **Phase 2:** Implement integration tests for the FastAPI backend and Celery workers using Testcontainers. Add mock rendering tests for the Docker pipeline.
3.  **Phase 3:** Develop a suite of AI Evals (LLM-as-a-Judge) for prompt regression testing.
4.  **Phase 4:** Create E2E Playwright scripts for the Next.js frontend and automated full-pipeline execution tests. Set up CI/CD workflows (GitHub Actions) to run these tests automatically on PRs.
