# AetherOS — Living Specification

## Project Vision

AetherOS is the ultimate AI orchestration and management platform that combines the best ideas from AG2, CrewAI, LangGraph, DSPy, Pydantic AI, Hermes, Bub, and TradingAgents into one unified, self-improving system with a powerful meta-agent called **Prime**.

## Core Principles

- Everything is versioned (AetherGit)
- Every action is logged (Tape)
- The system knows itself (Prime)
- Continuous self-improvement
- Beautiful and usable across web, desktop, and mobile

## Current Status (as of April 23, 2026)

- Initial monorepo scaffolding complete
- Basic Pydantic models for AetherCommit and TapeEntry
- FastAPI backend with health and tape endpoints
- Repository: https://github.com/MJ-Coder83/aetheros

## 90-Day Roadmap

- **Weeks 1-2**: Foundation (Tape, AetherGit, Database, CLI)
- **Weeks 3-8**: Core Intelligence (DSPy, Prime v1, Full AetherGit)
- **Weeks 9-16**: Full Experience (Prime Console, Multi-platform UI)
- **Weeks 17-26**: Production Readiness

## Priority Features (Week 1)

1. Living Spec document
2. Makefile + developer tooling
3. PostgreSQL integration
4. Tape service
5. Basic AetherGit

## Tech Stack

- Python 3.13+
- FastAPI + LangGraph + Pydantic v2 + DSPy
- PostgreSQL + Neo4j + Redis
- Next.js (web), Tauri (desktop), React Native (mobile)

## Success Metrics (End of Month 3)

- Users can create, version, and rewind agent crews
- Prime can explain the system and create simple domains
- Full AetherGit functionality works reliably
