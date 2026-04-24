# InkosAI — Living Specification

## Project Vision

InkosAI is the ultimate **self-governing AI operating system** and **universal visual development environment**. It empowers humans and AI to collaboratively design, build, simulate, iterate, and continuously improve **any type of digital interface** — web, mobile, desktop, TUI, video, podcast, games, 3D, and future interfaces — with no gaps in functionality.

## Core Architectural Principles

InkosAI is built around three tightly integrated representations of every system:

1. **Visual Canvas** — The beautiful, collaborative, node-based interface for humans and Prime.
2. **Folder-Tree Representation** — A clean, simple, filesystem-like structure that serves as the canonical, version-controlled source of truth for Domains, Canvases, and workflows.
3. **Agentic Graph** — The runtime execution graph used by Prime, Simulation Engine, and Debate Arena.

**The folder-tree is the stable backbone.** It makes Prime's reasoning deterministic, portable, auditable, and easy for coding agents to work with, while the visual Canvas provides the delightful user experience.

## Folder-Tree Integration (New Core Concept)

Every Domain and Canvas now has a **dual representation**:
- **Folder Tree** (source of truth) — stored on disk / in AetherGit
- **Visual Graph** (user-facing) — synchronized in real time with the folder tree.

**Folder Tree Structure Example** (Legal Research Domain):
```
Legal_Research_Domain/
├── agents/
│   ├── contract_analyst/
│   │   ├── role.md
│   │   ├── goals.md
│   │   ├── tools/
│   │   └── examples/
│   └── compliance_checker/
├── skills/
│   ├── contract_analysis.py
│   └── risk_scoring.py
├── workflows/
│   ├── full_contract_review/
│   │   ├── workflow.json
│   │   └── example_inputs/
├── templates/
│   └── analyze_contract_prompt.md
├── config/
│   └── domain_config.json
├── data_sources/
└── README.md
```

This structure is:
- Fully version-controlled with **AetherGit**
- Navigable and editable by **Prime** in "Folder Thinking Mode"
- Synchronized bidirectionally with the **Visual Canvas**
- Portable (easy to export/import as zip or git repo)

## Core Identity

- **Name**: InkosAI (from "Inkosi" = King/Chief in Zulu/Xhosa + AI)
- **Positioning**: The first true Operating System for Agentic AI, featuring deep self-awareness (Prime), immutable memory (Tape), version control (AetherGit), safe experimentation (Simulation), structured reasoning (Debate Arena), transparency (Explainability), and a universal Domain Canvas.

## Key Differentiators

- Self-aware meta-agent (Prime) that deeply understands and improves the entire system
- Immutable, auditable memory (Tape)
- Advanced version control and safe experimentation (AetherGit + Worktrees)
- Continuous self-improvement (Skill Evolution + Proposals)
- Safe "what-if" testing (Real-Time Simulation Engine)
- Structured multi-agent reasoning (Debate Arena)
- Full decision transparency (Explainability Dashboard)
- Universal visual development (Domain Canvas with Plugin Nodes and AI Co-Pilot)

## Current Status (April 24, 2026)
 
- **Phase 1: Prime Enhancements (Completed)** -- Built the self-aware foundation with persistence (PostgreSQL), modular API, advanced introspection, LLM planning, semantic Tape querying, and basic auth.
- **Phase 2: Core Platform Superpowers (Completed)** — Delivered AetherGit, Simulation, Debate Arena, Semantic Tape Querying, and InkosGraph.
- **Phase 3: User Experience & Collaboration (Current Focus)** — Building the universal visual development environment (Domain Canvas).
- **Extremely strong, production-minded backend core**
- **High architectural quality, consistent testing discipline, and thoughtful governance patterns


## Domain Canvas — v5 Vision (Universal Visual Development Environment)

The Domain Canvas is the heart of InkosAI — a powerful, node-based visual workspace where humans and Prime collaborate to design, build, simulate, and evolve any type of digital interface.

### Tiered Support

**Tier 1: Browser-Native Frameworks**
React, Next.js, Vue, Angular, Svelte, Electron, Tauri, Figma, Framer, Webflow, Storybook — full live embedding, hot reload, natural language editing, and two-way collaboration.

**Tier 2: High-Fidelity Emulation**
Flutter, React Native, .NET MAUI, SwiftUI, Jetpack Compose, WPF, Qt — AI-assisted rendering, interaction simulation, device frames, and semantic element detection.

**Tier 3: TUI / Terminal Interfaces**
Go (Bubble Tea), Rust (Ratatui), Python (Textual) — Visual TUI Layout Editor with drag-and-drop, AI Co-Pilot for configuration, natural language commands, and real-time preview.

**Tier 4: Plugin Nodes & Embedded Tools**
Godot, Unity, Unreal, Blender, DaVinci Resolve, Adobe Suite, VS Code, and any proprietary tool — full live embedding, deep agentic integration via Agent Bridge, and cross-tool orchestration.

### Cross-Tier Capabilities

- Natural language editing and AI Co-Pilot mode
- Element tagging and referencing
- Real-time simulation, Tape overlay, and AetherGit versioning
- Multi-user collaboration
- Visual diffing, ghost mode, and explainability integration

## Plugin Architecture & Marketplace

- Secure Plugin Node system with sandboxing, fine-grained permissions, and audit logging
- Agent Bridge for structured, safe agent-to-plugin communication
- Marketplace with discovery, ratings, monetization models, and governance

## Strategic Recommendations

- LLM Integration for complex goal decomposition
- Deeper historical Tape analysis in Introspection
- Agent-specific Git Worktree usage
- Semantic/Natural Language querying over Tape

### Future Technical Considerations (from Independent Review)

- **Heuristic Ceiling**: The ArgumentQualityScorer and BiasDetector currently rely on regex-based logic. While effective for V1, the system's reasoning intelligence will eventually plateau. Plan to upgrade these to semantic embedding comparisons or LLM-based evaluators for higher-quality debate analysis and bias detection.
- **Tape Memory Growth**: As an event-sourced system, the immutable Tape will grow indefinitely over time. Implement a snapshotting mechanism (periodic state collapse into a single record) to maintain performance while preserving full auditability of the event log.

## Success Metrics (End of Month 9)

- Prime can autonomously understand, propose, evolve, simulate, debate, and explain the entire system
- Users can build and iterate on any type of UI using the Domain Canvas
- InkosAI functions as a true self-governing, explainable, and universal creative operating system

## Tech Stack

Python 3.13+, FastAPI, LangGraph, Pydantic, DSPy, PostgreSQL, Neo4j, Next.js 16, Tailwind, shadcn/ui, React Flow
