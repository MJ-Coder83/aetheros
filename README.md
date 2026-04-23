# AetherOS

> The Ultimate AI Orchestration Platform — unify, version, and evolve your AI agents.

AetherOS combines the best ideas from AG2, CrewAI, LangGraph, DSPy, Pydantic AI, Hermes, Bub, and TradingAgents into one **unified, self-improving system** powered by a meta-agent called **Prime**.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **AetherGit** | Every action is versioned — create, rewind, and branch agent workflows like code |
| **Tape** | Immutable event log — every agent action is recorded and queryable |
| **Prime** | The meta-agent that knows the system and orchestrates self-improvement |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/MJ-Coder83/aetheros.git
cd aetheros

# Install dependencies (requires uv)
uv sync

# Start the dev server
make dev

# Run tests
make test

# Lint & format
make lint && make format
```

## Tech Stack

- **Backend**: Python 3.13+ · FastAPI · LangGraph · Pydantic v2 · DSPy
- **Database**: PostgreSQL · Neo4j · Redis
- **Frontend**: Next.js (web) · Tauri (desktop) · React Native (mobile)

## Project Structure

```
aetheros/
├── apps/web/              # Next.js web application
├── packages/
│   ├── core/              # Core models (AetherCommit)
│   ├── aethergit/         # Versioned agent orchestration
│   ├── tape/              # Immutable event logging
│   ├── prime/             # Meta-agent intelligence
│   ├── ui/                # Shared UI components
│   └── types/             # Shared type definitions
├── services/
│   ├── api/               # FastAPI backend
│   └── workers/           # Background workers
├── docs/                  # Living specification & docs
├── tests/                 # Test suite
└── scripts/               # Build & deploy scripts
```

## License

MIT
