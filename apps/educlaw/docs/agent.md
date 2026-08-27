## Implemented (local slice)

Working harness: Pydantic AI loop, Dagestan memory, compaction, steering queue, Docker Manim sandbox, permission modes, `ty`/syntax diagnostics, on-demand skills, Rich TUI, optional Kitaru wrap (`kitaru.adapters.pydantic_ai`), Logfire spans, and an offline evals smoke.

- Install and commands: [README.md](../README.md)
- Loop and modules: [harness.md](harness.md)
- Memory: [memory.md](memory.md)
- Sandbox: [sandbox.md](sandbox.md)
- Permissions: [permissions.md](permissions.md)
- Durable: [durable.md](durable.md)

Deferred: Modal sandboxes, remote Kitaru swarm, full `ty` LSP client, large eval suite.

---

- In a tests run by LangChain on Terminal-Bench changing only the harness with same model moved a coding agent from 30th place to top 5. 

- The model isn’t what makes a coding agent good. The harness is. So I am building a harness for Manim coding agents.  

- Remember there is a leaked codebase of Claude code. There are open source coding agents like opencode, PI, Tau and Aider/

- For a developer today, its very hard to engineer the most components of LLMs without serious compute and data. So Harness is sth every developer can engineer to squeeze out the performance.

- We name this coding harness as Educlaw. 
- There is a difference between good old ReAct pattern and Agent harness. 

- Educlaw should run from tui and also as headless agent in the sandbox for the UI. It should also let run the swarm of AI agents on cloud and also run on parallel on a cloud platform. 

- First I'll build the Agent loop via Pydantic AI. 
- Then I'll make the build around the loop with durable execution with Pydantic durable agents. And then the catalogue of planners, builders, explorers, and subagents. 
- Finally, a custom benchmark similar to Terminal-Bench, AI evals for regressions, observability with Logfire and deployments to cloud. 


- Language Server Protocol (LSP)
- The tighter these feedback loops, the faster the agent converges on working code.
- ty LSP server. It is a cheapest way to get feedback on code changes. 

- There are 6 essential modules: LLM providers, LSP server, Memory, Skills, Sandbox, and Permissions. These are essential for context engineering and security. 

- The context window of the LLM is a budget. The model might suffer from context decay. Hence, the harness needs to implement compaction techniques such as summarization, truncation, or just clearing the window.

- Interaction with harness: 
    - Interactive mode which is a TUI wired to one live session
    - Remote mode which is an agent runtime (Kitaru) runs N headless harnesses in parallel on a server, 

- AI evals & Observability layer powered by logfire. It records every model call and tool call, and turns a bad prompt tweak into a failing regression score before your users feel it in production.

- Anthropic is well known for continually optimizing their models for coding tasks. That’s why with every release their models get worse and worse at writing, while better and better at coding.

- On top of the agent loop, we have 6 modules + compaction that transform the agent loop into a headless harness. 

## The coding Harness

- TUI
- Runtime
- Context Engineering
- LLM Providers
- Permissions
- Memory
- LSP server
- AI Evals
- Skills
- Sandbox
- Tools

-> Model call, Repeat, tool call, Append result to memory, Repeat.

- LLM Providers: Hosted on Modal.com

- Sandbox: an agent that runs bash can break things. We wrap the bash and file-I/O tools to execute inside a sandbox (Docker locally, Modal Sandboxes remotely) instead of on your machine.

- Permissions: the permission layer is the most important guardrail: it asks you before running every action, or only the risky ones, depending on the mode. For example, it pauses before a destructive bash command like rm -rf and waits for your approval. This is similar to Claude Code’s default, edit, and auto modes.

- Memory: The iconic AGENTS.md that carries your project instructions plus a MEMORY.md 

- Skills: the omnipresent skills feature that encodes reusable workflows loaded only when invoked, so the context window doesn’t get bloated with all your instructions at once. The repo already ships a set of skills under .decode/skills/ that you can try out of the box.

- LSP server: a key component of a coding agent. It keeps an index of all your variables and functions. The loop gets syntax and semantic information about the codebase through 2 channels instead of brute-forcing through it or waiting for the code to run. On demand, the model asks where a symbol is defined, who calls it, what its real contract is, and what’s broken in a file. The model gets 1 precise file:line answer. After each edit, a fast syntax checker feeds its findings back into the loop. The agent fixes a type error in the same turn, before running/compiling any code. The cheapest feedback loop in the system.

- Compaction: not a module but a behavior of the harness itself that helps keep the context window as small as possible. The most iconic strategy is to compact the window once it goes over a threshold, squashing the window’s old head into a summary + keeping the recent interactions fresh: [summary, *tail]. You can also call this manually via /compact or simply clean the whole context window via /clear.

## The Steering Queue:
What happens when you send a new command and the agent is already mid-task?

- We should implement steering queue + priority gate. Input is buffered the instant it arrives into the steering queue and injected only at a safe boundary: before the next model call, never mid-tool-call. The gate decides how to process the messages from the queue: steer now, answer later, or abort.
 
- The steering queue can be a simple in memory FIFO queue. No need for a complex queue infrastructure like RabbitMQ.

## The remote Mode.
- We use Kitaru, the agent runtime built by ZenML, which provides durability, replay and distributed HITL features.