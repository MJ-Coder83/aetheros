# InkosAI — Living Specification

## Project Vision

InkosAI is the ultimate **self-governing AI operating system** and **universal visual development environment**. It empowers humans and AI to collaboratively design, build, simulate, iterate, and continuously improve **any type of digital interface** — web, mobile, desktop, TUI, video, podcast, games, 3D, and future interfaces — with no gaps in functionality.

## Core Architectural Principles

InkosAI is built around three tightly integrated representations of every system:

1. **Visual Canvas** — The beautiful, collaborative, node-based interface for humans and Prime.
2. **Folder-Tree Representation** — A clean, simple, filesystem-like structure that serves as the canonical, version-controlled source of truth for Domains, Canvases, and workflows.
3. **Agentic Graph** — The runtime execution graph used by Prime, Simulation Engine, and Debate Arena.

**The folder-tree is the stable backbone.** It makes Prime's reasoning deterministic, portable, auditable, and easy for coding agents to work with, while the visual Canvas provides the delightful user experience.

## Folder-Tree Integration (Core Architectural Principle)

Every Domain and Canvas has a **dual representation**:

- **Folder Tree** (source of truth) — stored on disk / in AetherGit
- **Visual Graph** (user-facing) — synchronized in real time with the folder tree

**Folder Tree Structure Example** (Legal Research Domain):

```
Legal_Research_Domain/
├── agents/
│   ├── contract_analyst/
│   │   ├── role.md
│   │   ├── goals.md
│   │   ├── SKILL.md  <-- auto-generated
│   │   ├── tools/
│   │   └── examples/
│   └── compliance_checker/
│       ├── role.md
│       ├── goals.md
│       └── SKILL.md  <-- auto-generated
├── skills/
│   ├── contract_analysis.py
│   ├── contract_analysis_SKILL.md  <-- auto-generated
│   ├── risk_scoring.py
│   └── risk_scoring_SKILL.md  <-- auto-generated
├── workflows/
│   ├── full_contract_review/
│   │   ├── workflow.json
│   │   └── example_inputs/
├── templates/
│   └── analyze_contract_prompt.md
├── config/
│   └── domain_config.json
├── data_sources/
├── evaluation/
│   └── criteria.json
└── README.md
```

This structure is:

- Fully version-controlled with **AetherGit**
- Navigable and editable by **Prime** in "Folder Thinking Mode"
- Synchronized bidirectionally with the **Visual Canvas**
- Portable (easy to export/import as zip or git repo)

### How Folder-Tree Is Incorporated Throughout the App

| Component | How Folder-Tree Enhances It (No Breaking Changes) |
|----------------------------|----------------------------------------------------|
| **Prime** | New "Folder Thinking Mode" — Prime can navigate, read, search, and propose changes using simple paths (`/agents/contract_analyst/`) |
| **One-Click Domain Creation** | Now generates both the Domain Blueprint **and** its clean folder-tree structure |
| **Domain Canvas** | Dual-mode view: **Visual Mode** ↔ **Folder Mode** (one-click switch, fully synchronized) |
| **AetherGit** | The folder tree is the primary source of truth for commits, branches, and rewinds |
| **Tape** | Every folder operation is logged (`prime.folder_created`, `prime.file_modified`, `prime.directory_listed`) |
| **Skill Evolution Engine** | Evolutions are expressed as precise folder operations (create/move/edit files) |
| **Self-Modification Proposals** | Proposals can include exact file/folder changes with visual diffs |
| **Plugin System** | Plugins can read/write to the domain's folder tree via the Agent Bridge |
| **Simulation Engine** | Simulations run on temporary folder branches (`/experiments/...`) |

All existing functionality remains exactly as it is. The folder-tree is an **additional layer** that makes the system more reliable, portable, and developer-friendly.

### GitNexus-Inspired Enhancements

Three new capabilities enhance the folder-tree system without breaking existing features:

1. **Automatic SKILL.md Generation** -- Prime automatically creates and maintains `SKILL.md` files for every agent and skill, describing capabilities, dependencies, and usage examples. These files are used by the Impact Analyzer and Dependency Graph Builder for deeper reasoning.

2. **Impact Analysis** (`assess_impact(path)`) -- Prime can predict what will break if a file, agent, or skill is changed. Reports direct/transitive dependents, severity (LOW/MEDIUM/HIGH/CRITICAL), and mitigation suggestions. All analyses logged to the Tape.

3. **Dependency Graph View** -- Inside Folder Mode, users can toggle a Sigma.js-style interactive knowledge graph showing symbols, imports, and cross-agent dependencies. Four edge types: IMPORT, REFERENCE, STRUCTURAL, SEMANTIC.

4. **Semantic Dependency Resolution** -- Prime detects and visualizes cross-file and cross-agent dependencies from Python imports, markdown references, structural parent-child relationships, and keyword-based semantic inference.

API endpoints added:
- `POST /folder-tree/impact/{domain_id}` -- Impact analysis
- `GET /folder-tree/dependency-graph/{domain_id}` -- Dependency graph
- `POST /folder-tree/skill-md/{domain_id}` -- Generate all SKILL.md files
- `PUT /folder-tree/skill-md/{domain_id}/{path}` -- Update single SKILL.md
- `POST /folder-tree/skill-md/parse` -- Parse SKILL.md content

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
- **Folder-Tree as stable backbone** — deterministic, portable, version-controlled source of truth

## Current Status (April 24, 2026)

- **Phase 1: Prime Enhancements (Completed)** — Built the self-aware foundation with persistence (PostgreSQL), modular API, advanced introspection, LLM planning, semantic Tape querying, and basic auth.
- **Phase 2: Core Platform Superpowers (Completed)** — Delivered AetherGit, Simulation, Debate Arena, Semantic Tape Querying, and InkosGraph.
- **Phase 3: User Experience & Collaboration (Current Focus)** — Building the universal visual development environment (Domain Canvas) with dual-mode Visual ↔ Folder view.
- Extremely strong, production-minded backend core
- High architectural quality, consistent testing discipline, and thoughtful governance patterns

## Domain Canvas — v5 Vision (Universal Visual Development Environment)

The Domain Canvas is the heart of InkosAI — a powerful, node-based visual workspace where humans and Prime collaborate to design, build, simulate, and evolve any type of digital interface.

### Dual-Mode View

- **Visual Mode** — The traditional node-based canvas with drag-and-drop, live preview, and AI Co-Pilot
- **Folder Mode** — The canonical folder-tree representation, synchronized in real time with the visual canvas

One-click switch between modes; changes in either mode are immediately reflected in the other.

### Implementation (Phase 1 — April 2026)

The Domain Canvas UI is implemented in `apps/web/src/app/canvas/page.tsx` with the following architecture:

**Frontend Components:**
- `CanvasPage` — Main route at `/canvas` with header, mode toggle, and layout selector
- `ModeToggle` — One-click switch between Visual and Folder modes
- `LayoutSelector` — Choose from Smart Auto, Layered, Hub & Spoke, Clustered, and Linear layouts
- `VisualCanvasView` — Interactive node-based canvas with:
  - SVG edge rendering (dependency, flow, data, control, group types)
  - Zoom controls (50%–200%)
  - Node selection panel showing label, type, status, folder path, and description
  - Grid background with scale-aware spacing
- `FolderTreeView` — Canonical folder-tree representation with:
  - Expandable/collapsible directories
  - File search filtering
  - File size display
  - Selection highlighting synchronized with visual canvas
- `FolderThinkingPanel` — Sidebar showing Prime's folder navigation actions in real time
- `PrimeFeatureBar` — Quick-access links to Simulate, Explain, Proposals, and Domains pages

**Integration Points:**
- **Navbar** — `/canvas` added to main navigation with Network icon
- **Command Palette** — "Open Domain Canvas" command added for ⌘K access
- **Prime Features** — Canvas header includes quick-access links to Simulation, Explainability, Proposals, and Domain Creator
- **Folder Thinking Mode** — Live panel shows Prime actions (`folder_navigate`, `folder_read`, `folder_search`, `file_modified`) with timestamps

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
- Folder-tree synchronization across all modes

## Plugin Architecture & Marketplace

- Secure Plugin Node system with sandboxing, fine-grained permissions, and audit logging
- Agent Bridge for structured, safe agent-to-plugin communication
- Plugins can read/write to the domain's folder tree via the Agent Bridge
- Marketplace with discovery, ratings, monetization models, and governance

## Strategic Recommendations

- LLM Integration for complex goal decomposition
- Deeper historical Tape analysis in Introspection
- Agent-specific Git Worktree usage
- Semantic/Natural Language querying over Tape
- Folder-tree as the primary interface for coding agents interacting with InkosAI

### Future Technical Considerations (from Independent Review)

- **Heuristic Ceiling**: The ArgumentQualityScorer and BiasDetector currently rely on regex-based logic. While effective for V1, the system's reasoning intelligence will eventually plateau. Plan to upgrade these to semantic embedding comparisons or LLM-based evaluators for higher-quality debate analysis and bias detection.
- **Tape Memory Growth**: As an event-sourced system, the immutable Tape will grow indefinitely over time. Implement a snapshotting mechanism (periodic state collapse into a single record) to maintain performance while preserving full auditability of the event log.

## One-Click Domain Creation

InkosAI enables instant creation of complete, specialised domains from a simple natural language description. This feature unifies blueprint generation, folder-tree scaffolding, Prime validation, and AetherGit versioning into a single, auditable workflow.

### Core Flow

1. **Blueprint Generation** — Parse the natural language description and auto-generate a complete `DomainBlueprint` with agents, skills, workflows, and configuration.
2. **Validation** — Run the `BlueprintValidator` to check completeness, safety, uniqueness, and naming conventions.
3. **Proposal Submission** — Submit the blueprint as a Proposal for human approval (with automatic risk assessment).
4. **Registration** — Upon approval, register the domain, create the canonical folder tree, run Prime's Folder Thinking Mode validation, and commit the tree to AetherGit.

### Architecture

```
DomainCreationEngine
├── generate_domain_blueprint()      — NL → DomainBlueprint
├── create_domain_from_description() — Full pipeline (generate + validate + propose)
├── register_domain()                — Blueprint → DomainRegistry + FolderTree + AetherGit
├── validate_blueprint()             — Standalone validation
├── list_domains() / get_domain()    — Registry queries
└── get_blueprint() / list_blueprints() — Blueprint store queries

OneClickDomainCreationEngine (extended pipeline)
├── generate_domain_blueprint()      — Inherited from DomainCreationEngine
├── generate_folder_tree()           — Auto-generate canonical folder structure
├── generate_starter_canvas()       — Optional starter canvas for the domain
└── create_domain_from_description() — Full pipeline with folder tree + canvas
```

### API Endpoints

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/domains/create` | POST | Create domain from natural language description |
| `/domains/one-click` | POST | One-click creation with folder tree + optional starter canvas |
| `/domains/blueprint` | POST | Generate blueprint only (no proposal) |
| `/domains/register` | POST | Register domain after proposal approval |
| `/domains` | GET | List all registered domains |
| `/domains/{id}` | GET | Get domain by ID |
| `/domains/blueprints` | GET | List all stored blueprints |
| `/domains/blueprints/{id}` | GET | Get blueprint by ID |

### Prime Console Integration

Users can create domains directly from the Prime Console using natural language:

- **"Create a Legal Research domain"** — Creates domain with starter canvas
- **"Make a Finance domain for trading"** — Custom domain from description

The Prime Console now detects domain creation requests and calls the One-Click Domain Creation API, providing real-time feedback with:
- Generated domain name and ID
- Agent, skill, and workflow counts
- Folder tree structure preview
- Starter canvas status (if included)
- Proposal submission confirmation

### Integration Points

| System | Integration |
|--------|-------------|
| **Prime / Introspector** | Folder Thinking Mode validates the generated tree structure (`folder_navigate`, `folder_read`, `folder_search`) |
| **Folder Tree** | Canonical folder tree is generated automatically during registration (`FolderTreeService.create_tree`) |
| **AetherGit** | Each registered domain gets an initial AetherGit commit on its own branch (`domain/{domain_id}`) |
| **Tape** | Every step is logged: `domain.blueprint_generated`, `domain.creation_requested`, `domain.registered`, `prime.folder_tree_created` |
| **Proposals** | All new domains require Proposal approval before registration (configurable via `DomainConfig.requires_human_approval`) |

### Safety Guarantees

- Duplicate domain names and IDs are prevented
- Generated content is validated for completeness and safety
- All creation events are logged to the immutable Tape
- Both fully-automatic and human-guided creation modes are supported
- High-risk domains (legal, healthcare, finance) automatically require human approval

## Personalized Intelligence Profile

InkosAI maintains a **Personalized Intelligence Profile** for each user — a living, adaptive model of expertise, preferences, working style, goals, and interaction patterns that Prime uses to tailor its behaviour, suggestions, and communication style.

### Architecture

The profile system has been consolidated into a single, unified `UserProfile` model that embeds the `IntelligenceProfile` (domain expertise, preference inference, interaction tracking) alongside rich personalization data (goals, skills, working style, folder-tree and AetherGit integration).

```
UserProfile (unified model)
├── IntelligenceProfile (embedded)
│   ├── DomainExpertise — Per-domain expertise level (novice → expert) with score tracking
│   ├── UserPreference — Categorised preference values (verbosity, risk_tolerance, detail_level, etc.)
│   ├── InteractionSummary — Aggregate stats (total_interactions, approval_rate, avg_depth)
│   ├── BehaviouralSignals — Freeform key-value signals
│   └── AdaptationCount — Number of profile adaptations
├── WorkingStyleConfig — primary_style, communication_style, automation_preference
├── UserPreferenceSetting — Key-value preferences (explicit or inferred)
├── UserGoal — Tracked goals with progress, priority, and status
├── LearnedSkill — Skills learned through interactions, with proficiency tracking
├── InteractionPattern — Detected usage patterns (time_of_day, domain_preference, etc.)
├── HistorySummary — Aggregate session and interaction statistics
├── folder_tree_path — Path in folder-tree where profile data is stored
├── aethergit_commit_id — Last AetherGit commit hash for this profile
└── ProfileStorage — Persistence layer (InMemory / Filesystem / AetherGit)

ProfileStorage (CRUD + helpers)
├── get_or_create_profile() / update_profile() / delete_profile()
├── set_preference() / get_preference() / update_preferences()
├── update_working_style()
├── add_goal() / update_goal() / complete_goal() / delete_goal()
├── add_or_update_skill() / get_skill() / list_skills()
├── record_pattern() / list_patterns()
├── update_history_summary() / record_session()
├── sync_to_aethergit() / export_profile() / import_profile()
└── get_profile_summary()

IntelligenceProfileEngine (backward-compatible facade)
├── record_interaction() — Updates expertise + interaction summary + inferred preferences
├── set_preference() / get_effective_preference()
├── create_snapshot() / rollback_to_snapshot() / list_snapshots()
├── get_domain_summary() / get_recommendation_context()
├── merge_profiles() — Merge source profile into target
├── archive_profile() / suspend_profile() / reactivate_profile()
└── ExpertiseAssessor — Infers expertise from interaction patterns
    PreferenceInferrer — Derives preferences from observed behaviour

ProfileLearningEngine (separate module: profile_learning.py)
├── TapeBehaviorAnalyzer — Extracts patterns from Tape entries
├── ProposalPatternAnalyzer — Analyzes approval/rejection tendencies
├── CanvasInteractionAnalyzer — Studies canvas usage patterns
├── FeedbackAnalyzer — Processes explicit feedback signals
├── FolderTreeAnalyzer — Infers organizational preferences
├── learn_for_user() — Full behavioral analysis for one user
├── batch_learn_all() — Batch learning across all users
├── suggest_profile_updates() — Generate reviewable suggestions
└── learn_from_event() — Incremental single-event learning
```

### Storage Backends

| Backend | Use Case |
|---------|----------|
| **InMemoryProfileStore** | Testing and development |
| **FilesystemProfileStore** | Persistent storage, folder-tree linked |
| **AetherGit** | Version-controlled profile storage (via `sync_to_aethergit`) |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profiles/interactions` | POST | Record a user interaction |
| `/profiles/{user_id}` | GET | Get user profile |
| `/profiles/{user_id}` | POST | Get or create user profile |
| `/profiles` | GET | List all profiles |
| `/profiles/preferences` | POST | Set a preference value (IntelligenceProfile)
| `/profiles/{user_id}/preferences/{category}` | GET | Get effective preference for category |
| `/profiles/{user_id}/snapshots` | POST | Create profile snapshot |
| `/profiles/{user_id}/snapshots` | GET | List profile snapshots |
| `/profiles/{user_id}/rollback/{snapshot_id}` | POST | Rollback profile to snapshot |
| `/profiles/{user_id}/domains` | GET | Get domain expertise summary |
| `/profiles/{user_id}/context` | GET | Get recommendation context for Prime |
| `/profiles/merge` | POST | Merge two profiles |
| `/profiles/{user_id}/archive` | POST | Archive profile |
| `/profiles/{user_id}/suspend` | POST | Suspend profile |
| `/profiles/{user_id}/reactivate` | POST | Reactivate suspended profile |
| `/profiles/{user_id}/summary` | GET | Get full profile summary |
| `/profiles/{user_id}/details` | PATCH | Update display_name, email, bio |
| `/profiles/{user_id}/user-preferences` | POST | Set UserProfile preference (key-value) |
| `/profiles/{user_id}/working-style` | PATCH | Update working style configuration |
| `/profiles/{user_id}/goals` | POST | Add a new goal |
| `/profiles/{user_id}/goals` | GET | List goals |
| `/profiles/{user_id}/goals/{goal_id}` | PATCH | Update a goal |
| `/profiles/{user_id}/goals/{goal_id}/complete` | POST | Complete a goal |
| `/profiles/{user_id}/goals/{goal_id}` | DELETE | Delete a goal |
| `/profiles/{user_id}/skills` | POST | Add or update a learned skill |
| `/profiles/{user_id}/skills` | GET | List skills |
| `/profiles/{user_id}/patterns` | POST | Record an interaction pattern |
| `/profiles/{user_id}/patterns` | GET | List interaction patterns |
| `/profiles/{user_id}/sessions` | POST | Record a completed session |
| `/profiles/{user_id}/sync` | POST | Sync profile to AetherGit |
| `/profiles/{user_id}/export` | GET | Export profile as JSON |

### Frontend Integration

- **Profile Page** (`/profile`) — Full profile view with click-to-edit preference sliders, snapshot creation/rollback, domain expertise display, working style config, goals, and learned skills
- **Prime Console** (`/prime`) — Profile sidebar card, profile-aware query handling, and "My profile" quick-action button
- **Dashboard** — `ProfileSummaryCard` widget showing interaction count, approval rate, top domains, working style, and key preferences
- **Command Palette** — "View Intelligence Profile" command (⌘K → Brain icon)

### Integration Points

| System | Integration |
|--------|-------------|
| **Prime** | Uses `getRecommendationContext` to tailor responses, verbosity, and suggestions to user expertise, working style, and preferences |
| **Tape** | Every profile update is logged (`profile.interaction_recorded`, `profile.preference_set`, `profile.snapshot_created`, `profile.rollback`, `profile.goal_added`, `profile.skill_updated`, `profile.pattern_recorded`) |
| **Proposals** | Approval/rejection events feed the profile's interaction summary and expertise assessor |
| **Domains** | Domain interaction frequency drives expertise level upgrades (novice → intermediate → advanced → expert) |
| **Folder Tree** | Profile data can be stored in the folder-tree structure via `FilesystemProfileStore` |
| **AetherGit** | Profile changes can be synced to AetherGit for version control (`sync_to_aethergit`) |
| **Profile Learning** | `ProfileLearningEngine` continuously analyzes Tape, Proposals, Canvas, Feedback, and Folder-Tree to refine the profile |

### Backward Compatibility

The `IntelligenceProfileEngine` facade is fully backward-compatible — existing code that imports from `packages.prime.intelligence_profile` continues to work. The old `IntelligenceProfile` model is now embedded within `UserProfile`, and convenience properties on `UserProfile` allow transparent access to `domain_expertise`, `interaction_summary`, and `adaptation_count`.

### Safety Guarantees

- Profile data is user-scoped — no cross-user leakage
- Snapshots enable rollback to any prior state
- Preferences have confidence scores; low-confidence inferences are not applied automatically
- Profile status lifecycle: `active → suspended → archived`, with reactivation support
- All mutations are logged to the immutable Tape
- Explicit preferences always override inferred values with full confidence

## Success Metrics (End of Month 9)

- Prime can autonomously understand, propose, evolve, simulate, debate, and explain the entire system
- Prime can navigate and reason about domains using Folder Thinking Mode
- Users can build and iterate on any type of UI using the Domain Canvas (Visual or Folder mode)
- InkosAI functions as a true self-governing, explainable, and universal creative operating system

## Tech Stack

Python 3.13+, FastAPI, LangGraph, Pydantic, DSPy, PostgreSQL, Neo4j, Next.js 16, Tailwind, shadcn/ui, React Flow
