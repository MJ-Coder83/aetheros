# InkosAI

> The Ultimate AI Orchestration Platform — unify, version, and evolve your AI agents.

InkosAI combines the best ideas from AG2, CrewAI, LangGraph, DSPy, Pydantic AI, Hermes, Bub, and TradingAgents into one **unified, self-improving system** powered by a meta-agent called **Prime**.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **AetherGit** | Every action is versioned — create, rewind, and branch agent workflows like code |
| **Tape** | Immutable event log — every agent action is recorded and queryable |
| **Prime** | The meta-agent that knows the system and orchestrates self-improvement |

## Quick Start

### 🚀 Five-Minute Launch

```bash
# 1. Clone and enter directory
git clone https://github.com/inkosai/inkosai.git
cd inkosai

# 2. Create environment file
cp .env.example .env

# 3. Start everything (requires Docker)
docker-compose up -d

# 4. Check health
curl http://localhost:8000/api/health

# 5. Open the web UI
open http://localhost:3000
```

**Default credentials:**
- Username: `admin`
- Password: See `.env` file

### Development Setup

```bash
# Install dependencies
uv sync

# Start development server
uv run uvicorn services.api.main:app --reload

# Run tests (2100+ tests)
uv run pytest

# Lint and format
uv run ruff check . && uv run ruff format . && uv run mypy packages/ services/
```

### Next Steps

- **User Guide**: Learn about Domains, Canvas, Swarm, and Prime → [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **API Documentation**: Full API reference → [docs/API.md](docs/API.md)
- **Deployment**: Docker, K8s, production setup → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Architecture**: Technical specification → [docs/LIVING_SPEC.md](docs/LIVING_SPEC.md)

## Tech Stack

- **Backend**: Python 3.13+ · FastAPI · LangGraph · Pydantic v2 · DSPy
- **Database**: PostgreSQL · Neo4j · Redis
- **Frontend**: Next.js (web) · Tauri (desktop) · React Native (mobile)

## Project Structure

```
inkosai/
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
