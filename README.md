# ZeroTrust.Agent

**An ultra-low latency (<5ms) semantic firewall and multi-agent security proxy.**

ZeroTrust.Agent is an enterprise-grade, transparent middleware proxy designed to neutralize prompt injection, data exfiltration, and autonomous AI agent hijacking in multi-agent LLM systems. It enforces "Semantic Isolation" between LLM reasoning, tool calling, and external data access.

## Features

- **Inbound Intent Mapping:** Heuristic scanner (and future embedding engine) intercepts and neutralizes high-risk prompt injections.
- **Outbound Data Loss Prevention (DLP):** Transparently scrubs outputs (AWS keys, CC numbers, API keys) before they reach the user or external systems.
- **Deterministic Schema Validation:** Utilizes Pydantic to strictly validate LLM-generated tool execution payloads against a predefined Registry.
- **Context Provenance Ledger:** Redis-backed ledger tracks agent sessions. If an agent ingests untrusted data, it is dynamically downgraded to a "Read-Only" role.
- **Asynchronous Telemetry & CISO Dashboard:** SQLite-backed, fire-and-forget telemetry engine hooked into a sleek React dashboard for live threat monitoring.

## Architecture

1. **Proxy Layer:** Python / FastAPI (async routing)
2. **State Ledger:** Redis
3. **Telemetry Database:** SQLite / aiosqlite
4. **Control Plane:** React + TailwindCSS + Vite + Nginx

##The Security Pipeline
```text
                        ┌─────────────────────────┐
                        │      User Request       │
                        └────────────┬────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │        ZeroTrust.Agent         │
                    │      AI Security Gateway       │
                    └────────────┬───────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
 ┌────────────────┐     ┌────────────────┐    ┌─────────────────┐
 │ Intent Scanner │     │ Context Ledger │    │ Telemetry Engine│
 │ Prompt Defense │     │ Redis Trust DB │    │ SQLite Logging  │
 └────────────────┘     └────────────────┘    └─────────────────┘
                                 │
                                 ▼
                 ┌────────────────────────────────┐
                 │  OpenAI-Compatible LLM / Agent │
                 └────────────────┬───────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │      Model Response       │
                     └────────────┬─────────────┘
                                  │
          ┌───────────────────────┼────────────────────────┐
          │                       │                        │
          ▼                       ▼                        ▼
 ┌────────────────┐     ┌────────────────┐     ┌─────────────────┐
 │ Tool Validator │     │ DLP Scrubber   │     │ Event Logger     │
 │ Schema Checks  │     │ Secret Removal │     │ Threat Auditing  │
 └────────────────┘     └────────────────┘     └─────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │        Safe AI Response      │
                    └──────────────────────────────┘
```

## Quickstart

Run the entire ZeroTrust.Agent stack (Frontend Dashboard, Backend Proxy, and Redis) locally using Docker Compose.

```bash
# Clone the repository and boot the stack in detached mode
docker-compose up -d --build
```

### Accessing the Dashboard
Once the containers are running, access the live CISO Control Plane Dashboard at:
[http://localhost:3000](http://localhost:3000)

### Intercepting LLM Traffic
ZeroTrust.Agent is designed to be a drop-in replacement for any OpenAI-compatible API base URL. 

To secure an agent or application, simply point its `base_url` to the proxy endpoint running on port `8000`:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key", 
    # Point traffic to the local proxy!
    base_url="http://localhost:8000/v1" 
)

# This request will be inspected, validated, and logged by ZeroTrust.Agent
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Execute tool: get_user_data"}]
)
```
