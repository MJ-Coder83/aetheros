# InkosAI — Living Specification

## Project Vision

InkosAI is the ultimate **self-governing AI operating system** and **universal visual development environment**. It combines powerful agent orchestration, version control (AetherGit), immutable memory (Tape), and a meta-agent called Prime that deeply understands and continuously improves the entire system.

## Core Architectural Principles

InkosAI is built around three tightly integrated representations of every system:

1. **Visual Canvas** — The beautiful, collaborative, node-based interface for humans and Prime.
2. **Folder-Tree Representation** — The canonical, version-controlled source of truth (GitNexus-inspired enhancements included).
3. **Agentic Graph** — The runtime execution graph used by Prime, Simulation Engine, and Debate Arena.

The folder-tree is the stable backbone. It makes reasoning deterministic, portable, auditable, and easy for coding agents to work with, while the visual Canvas provides the delightful user experience.

## Folder-Tree Integration (GitNexus-Inspired)

Every Domain and Canvas has a dual representation:

- **Folder Tree** (source of truth) — stored on disk / in AetherGit
- **Visual Graph** (user-facing) — synchronized in real time

GitNexus-Inspired Enhancements:

- Automatic SKILL.md generation for agents and skills
- Impact analysis (assess_impact(path))
- Dependency Graph View toggle in Folder Mode
- Semantic dependency resolution in Prime's Folder Thinking Mode

## Key Features & Capabilities

- **One-Click Domain Creation** — Generate complete specialized domains with optional starter Canvas.
- **Domain Canvas (v5)** -- Full visual development environment with:
  - Dual-mode interface (Visual graph + Folder tree, one-click toggle)
  - Tiered UI Support (Tier 1: Browser-Native, Tier 2: High-Fidelity, Tier 3: Terminal/TUI, Tier 4: Plugin Nodes)
  - Key Node Types: Browser Node (live preview, element detection, NL editing), Terminal Node (TUI layout editor, AI co-pilot), Plugin Node (first-class Plugin SDK integration)
  - Smart Auto-Layout + Beautify button
  - Simulation Overlay (real-time metrics on every node)
  - Tape Overlay (live events flowing through canvas)
  - Natural Language Canvas Editing
  - Prime Co-Pilot Mode (UX issue detection, layout optimization, A/B variants, auto-optimizations)
  - AetherGit Versioning with visual diff and rewind
  - Swarm Integration (Quick Swarm + Governed Swarm, multi-domain support)
  - Full folder-tree dual representation (source of truth)
- **Swarm Mode** — Quick Swarm (Ruflo-like speed) and Governed Swarm (structured + auditable) in the Coding Domain, with basic multi-domain support.
- **Prime** — Self-aware meta-agent with Folder Thinking Mode, introspection, self-modification proposals, and cross-domain coordination.
- **Skill Evolution Engine** — Continuous improvement (enhance, create, merge, split, deprecate) with proposal workflow.
- **Real-Time Simulation Engine** — Safe what-if testing with isolation and rollback.
- **Multi-Agent Debate Arena** — Structured debates with bias detection and consensus tracking.
- **Explainability Dashboard** — Full decision tracing and factor analysis.
- **Advanced AetherGit** — Semantic search, intelligent merge, branch explorer, worktree management, commit comparison.
- **Plugin System + Marketplace** — Extensible architecture with Agent Bridge and Canvas integration.

## Current Status (April 26, 2026)

- Core backend (Tape, AetherGit, Prime, Skill Evolution, Simulation, Debate, Explainability) complete.
- Prime Console UI + Domain Canvas foundation complete.
- Folder-tree integration added as core architectural principle.
- Swarm capabilities implemented in Coding Domain (Quick + Governed modes).
- Plugin System + Marketplace development in progress with 4 agents.

## Development Roadmap

- Phase 1: Foundation & Core Intelligence (completed)
- Phase 2: Swarm, Domain Creation, Canvas, Plugin System (in progress)
- Phase 3: Multi-domain swarms, advanced plugin ecosystem, full production readiness

## Plugin Architecture & Marketplace

InkosAI features a secure, extensible Plugin System with a full Marketplace for discovery, installation, and governance of plugins that extend the platform's capabilities.

### Architecture

```
PluginManifest (core schema)
├── id, name, version, description, author
├── homepage, repository
├── permissions: PluginPermission[] — fine-grained access control
├── entry_point, min_platform_version, max_platform_version
├── tags, category, icon

InstalledPlugin (runtime state)
├── manifest: PluginManifest
├── status: installed | enabled | disabled | error | pending_install
├── enabled: bool
├── installed_at, updated_at
├── install_path
└── last_error

MarketplacePlugin (catalog entry)
├── manifest: PluginManifest
├── status: published | under_review | deprecated | removed
├── downloads, rating_avg, rating_count
├── published_at, updated_at
├── featured, verified
```

### Permission System

Every plugin declares the permissions it requires. Users review and selectively grant permissions at install time. Permissions are classified by risk level:

| Risk Level | Permissions | Description |
|------------|------------|-------------|
| **Low** | `folder_tree_read`, `domain_read` | Read-only access to non-sensitive data |
| **Medium** | `tape_read`, `canvas_read`, `agent_communicate` | Read access to activity/logs, canvas, inter-agent messaging |
| **High** | `folder_tree_write`, `tape_write`, `canvas_write` | Write access to core structures |
| **Critical** | `network_access`, `system_config` | External network calls, system configuration changes |

Permissions can be individually toggled during installation. A plugin that lacks a required permission will gracefully degrade or report an error rather than fail silently.

### Installation Flow

1. **Discover** — User browses the Marketplace or searches by category, tags, or keyword
2. **Review** — User selects a plugin and reviews its manifest, permissions, ratings, and download count
3. **Permission Grant** — User toggles individual permissions on/off (high-risk permissions shown in red/amber badges)
4. **Install** — System installs the plugin with granted permissions, logs `plugin.installed` to Tape
5. **Enable/Disable** — Plugin can be toggled without uninstalling; status changes logged to Tape

### Marketplace API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/marketplace/plugins` | GET | Discover/search plugins (query, category, tags, sort_by, limit, offset) |
| `/marketplace/plugins/{id}` | GET | Get plugin details |
| `/marketplace/plugins/{id}/install` | POST | Install a plugin (version, granted_permissions, user_id) |
| `/marketplace/plugins/{id}/uninstall` | POST | Uninstall a plugin |
| `/marketplace/installed` | GET | List installed plugins |
| `/marketplace/plugins/{id}/rate` | POST | Rate a plugin (score, review, user_id) |

### Frontend Integration

**Marketplace Page** (`/marketplace`):
- **Browse tab** — Search bar, category filters (Analytics, Automation, Communication, Data, Development, Integration, Productivity, Security), sort options (downloads, rating, newest, name), plugin cards with name/author/version/rating/downloads/category/featured/verified badges, high-risk permission warnings
- **Installed tab** — List of installed plugins with status badges (enabled=green, disabled=amber, error=red), uninstall button with confirmation dialog
- **Install dialog** — Permission review with per-permission toggle, risk-level badges (low=green, medium=amber, high=red), install confirmation
- **Uninstall dialog** — Confirmation with plugin name and version

**Prime Console** (`/prime`):
- **Plugins snapshot sidebar** — Shows all installed plugins with on/off status badges
- **Plugin query handling** — "show plugins", "installed plugins", "what plugins" queries return formatted plugin list with status, permissions, and author
- **Health/status response** — Includes plugin count in system overview
- **Help response** — Lists plugin-related queries in the help section
- **Quick action** — "Show plugins" quick-action button in the chat input bar

**Navigation**:
- **Navbar** — Marketplace entry with Store icon at `/marketplace`
- **Command Palette** — "Open Plugin Marketplace" command (⌘K → Store icon)

### Folder Tree Integration

Plugins with `folder_tree_read` or `folder_tree_write` permissions can access domain folder trees via the Agent Bridge. All folder operations by plugins are logged to the Tape with the plugin ID as the agent reference, ensuring full auditability of plugin-driven modifications.

### Tape Event Types

| Event Type | Trigger |
|------------|---------|
| `plugin.installed` | Plugin successfully installed |
| `plugin.uninstalled` | Plugin removed from system |
| `plugin.enabled` | Plugin toggled on |
| `plugin.disabled` | Plugin toggled off |
| `plugin.permission_granted` | Permission granted at install time |
| `plugin.permission_denied` | Permission denied at install time |
| `plugin.error` | Plugin encountered a runtime error |
| `plugin.rated` | User submitted a rating/review |

### Safety Guarantees

- All plugin operations are logged to the immutable Tape
- Fine-grained permissions prevent unauthorized access to system resources
- High-risk permissions require explicit user opt-in during installation
- Plugins run in sandboxed execution contexts via the Agent Bridge
- Marketplace entries are reviewed before publication (`under_review` status)
- Deprecated or malicious plugins can be removed by governance (`removed` status)
- Users can disable any plugin without uninstalling, preserving data integrity

## One-Click Domain Creation

InkosAI enables instant creation of complete, specialised domains from a simple natural language description. This feature unifies blueprint generation, folder-tree scaffolding, Prime validation, and AetherGit versioning into a single, auditable workflow.

### Core Flow

1. **Blueprint Generation** — Parse the natural language description and auto-generate a complete `DomainBlueprint` with agents, skills, workflows, and configuration.
2. **Validation** — Run the `BlueprintValidator` to check completeness, safety, uniqueness, and naming conventions.
3. **Proposal Submission** — Submit the blueprint as a Proposal for human approval (with automatic risk assessment).
4. **Registration** — Upon approval, register the domain, create the canonical folder tree, run Prime's Folder Thinking Mode validation, and commit the tree to AetherGit.

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

The Prime Console detects domain creation requests and calls the One-Click Domain Creation API, providing real-time feedback with generated domain name/ID, agent/skill/workflow counts, folder tree preview, starter canvas status, and proposal confirmation.

## Personalized Intelligence Profile

InkosAI maintains a **Personalized Intelligence Profile** for each user — a living, adaptive model of expertise, preferences, working style, goals, and interaction patterns that Prime uses to tailor its behaviour, suggestions, and communication style.

### Architecture

The profile system uses a unified `UserProfile` model that embeds the `IntelligenceProfile` (domain expertise, preference inference, interaction tracking) alongside personalization data (goals, skills, working style, folder-tree and AetherGit integration).

### Frontend Integration

- **Profile Page** (`/profile`) — Full profile view with preference sliders, snapshot creation/rollback, domain expertise, working style, goals, and learned skills
- **Prime Console** (`/prime`) — Profile sidebar card, profile-aware query handling, and "My profile" quick-action button
- **Dashboard** — `ProfileSummaryCard` widget
- **Command Palette** — "View Intelligence Profile" command (⌘K)

### Integration Points

| System | Integration |
|--------|-------------|
| **Prime** | Uses `getRecommendationContext` to tailor responses to user expertise and preferences |
| **Tape** | Every profile update logged (`profile.interaction_recorded`, `profile.preference_set`, etc.) |
| **Proposals** | Approval/rejection events feed expertise assessor |
| **Domains** | Domain interaction frequency drives expertise level upgrades |
| **Folder Tree** | Profile data stored via `FilesystemProfileStore` |
| **AetherGit** | Profile changes synced via `sync_to_aethergit` |
| **Profile Learning** | `ProfileLearningEngine` continuously analyzes Tape, Proposals, Canvas, Feedback, and Folder-Tree |

## Success Metrics (End of Month 3)

- Solo devs can create a Coding Domain and run powerful swarms in seconds.
- Prime can autonomously evolve skills and resolve cross-domain conflicts.
- Full visual + folder-tree dual representation works seamlessly.
- Plugin marketplace allows easy extension with external tools.

## Technical Debt Cleanup Notes (v5)

### Completed Cleanup (April 26, 2026)

1. **Mock Data Removal**
   - Moved all mock data generators from `canvas/page.tsx` to `__fixtures__/canvas-mocks.ts`
   - Production code now uses real API calls with proper empty states

2. **Error Handling Improvements**
   - Replaced silent catch blocks with proper error logging
   - Added `error` state for user-facing error messages
   - All canvas operations now surface errors to console and UI
   - API calls use `encodeURIComponent(domainId)` for safety

3. **Canvas Performance** (Future work)
   - Edge rendering still uses SVG `<line>` — consider Canvas API or WebGL for >200 nodes
   - Node virtualization to be implemented for large graphs
   - Memoization opportunities in `NodeCardV5` and `EdgeLine`

4. **Type Safety** (Future work)
   - Strict mode compliance needs full audit of `any` types
   - Canvas v5 types are well-defined but some internal functions need refinement

5. **Bundle Size** (Future work)
   - Lucide icons are already tree-shakable via individual imports
   - Consider dynamic imports for heavy canvas features

## Planning Methodologies Integration

InkosAI officially supports three leading AI planning methodologies as first-class Domains and Plugins:

### Gastown Domain

Multi-agent workspace orchestration domain providing persistent coordination, session management, and resource allocation for distributed agent systems.

**Key Agents:**
- Workspace Manager — Initializes and maintains multi-agent workspaces
- Agent Coordinator — Orchestrates agent interactions and message routing
- Session Manager — Manages session lifecycles and recovery
- Resource Allocator — Distributes computational resources
- Task Distributor — Matches tasks to agents with appropriate capabilities

**Key Workflows:**
- Workspace Initialization
- Multi-Agent Coordination
- Session Lifecycle Management

**Visual Style:** Indigo (#6366f1)

### GSD Domain (Get Shit Done)

Meta-prompting and phase-based autonomous development domain providing structured development cycles with context engineering and quality validation at each phase.

**Key Agents:**
- Phase Manager — Orchestrates the 6 GSD phases
- Context Engineer — Optimizes context for agent effectiveness
- Meta-Prompt Designer — Designs and refines meta-prompts
- Execution Tracker — Monitors task execution and identifies blockers
- Quality Validator — Enforces quality gates
- Implementation Builder — Executes implementation phase

**GSD Phases:**
1. Research
2. Design
3. Implement
4. Test
5. Deploy
6. Validate

**Visual Style:** Emerald (#10b981)

### BMAD Domain

Breakthrough Method for Agile AI-Driven Development providing sprint-based planning with multi-track coordination and breakthrough facilitation.

**Key Agents:**
- Sprint Planner — Plans sprints and coordinates across tracks
- Breakthrough Facilitator — Facilitates creative problem-solving sessions
- Agile Coach — Guides agile practices and ceremonies
- Track Coordinator — Manages Research, Design, Build, Review tracks
- Sprint Reviewer — Conducts sprint reviews and gathers feedback
- Implementation Executor — Executes sprint backlog items

**Key Workflows:**
- BMAD Sprint Cycle
- Breakthrough Session
- Track Coordination Flow

**Visual Style:** Amber (#f59e0b)

### Planning Super Domain

Unified planning environment combining Gastown, GSD, and BMAD methodologies with smart Prime orchestration and intelligent methodology selection.

**Key Agents:**
- Planning Orchestrator — Coordinates across all methodologies
- Methodology Selector — Recommends optimal methodology mix
- Conflict Resolver — Detects and resolves methodology conflicts
- Hybrid Tracker — Tracks progress across hybrid workflows
- Gastown Liaison — Bridges to Gastown methodology
- GSD Liaison — Bridges to GSD methodology
- BMAD Liaison — Bridges to BMAD methodology

**Key Workflows:**
- Hybrid Planning Pipeline
- Cross-Methodology Swarm
- Conflict Resolution Workflow

**Visual Style:** Violet (#8b5cf6)

### Cross-Methodology Swarm Support

**Hybrid Patterns:**
- GSD Research → BMAD Sprint Planning
- Gastown Execution → BMAD Sprint Review
- GSD Context Engineering → Gastown Coordination
- BMAD Breakthrough → GSD Build Phase
- Full Hybrid (all three methodologies)

**Conflict Resolution:**
- Debate Arena for agent discussions
- Simulation Engine for outcome prediction
- Prime Override for final decisions
- Methodology hierarchy (GSD > BMAD > Gastown for conflicts)

### Plugin Marketplace

Official plugins available for each methodology:
- `gastown-plugin` — Workspace orchestration commands
- `gsd-plugin` — Phase management and meta-prompting
- `bmad-plugin` — Sprint planning and breakthrough facilitation

## Tech Stack

Python 3.13+, FastAPI, LangGraph, Pydantic v2, PostgreSQL, Next.js 16, shadcn/ui, AetherGit (custom), Tape (immutable log)

## Production Readiness (Phase 1)

### Authentication & Authorization

**JWT-based Authentication:**
- Access tokens (60 min expiry) + refresh tokens (7 day expiry)
- bcrypt password hashing with salt
- Token blacklist via database (revocation support)
- All auth events logged to Tape

**User Roles:**
| Role | Access Level |
|------|-------------|
| admin | Full system access |
| operator | Domain management, proposals |
| viewer | Read-only, view canvas/simulations |

**Database Schema:**
- `users` — id, username, email, hashed_password, role, is_active, last_login
- `refresh_tokens` — jti, user_id, expires_at, revoked (for token revocation)

### Security Hardening

**Rate Limiting:**
- 120 requests per 60 seconds per IP
- Applied to public endpoints via middleware

**CORS:**
- Configurable allowed origins via env var
- Production: `CORS_ORIGINS=https://inkos.ai`

**Input Sanitization:**
- Pydantic v2 validation on all API requests
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via React escaping (frontend)

**Plugin Sandbox:**
- Deno-based plugin runtime in `/sandbox/plugin-executor.ts`
- Network whitelist enforcement
- Filesystem restricted to `/tmp/sandbox`
- 30-second execution timeout
- Process isolation via container

### Deployment

**Docker:**
- Multi-stage build for optimized image
- Non-root user (`inkosai`)
- Health check endpoints
- PostgreSQL + Redis services

**Docker Compose:**
```bash
docker-compose up -d
```
Services: postgres, redis, api, plugin-sandbox

**GitHub Actions:**
- Python: ruff, mypy, pytest
- Next.js: ESLint, tsc, build
- Docker: build test
- Security: vulnerability scan

**Environment Variables:**
- See `.env.example` for complete list
- Required: `DATABASE_URL`, `JWT_SECRET_KEY`, `REDIS_URL`
- Security: Rotate `JWT_SECRET_KEY` in production

### Operations

**Health Checks:**
- `/api/health` — Basic liveness
- Database + Redis connection validation

**Monitoring:**
- All events log to Tape (immutable audit log)
- Console logging for debugging
- Sentry integration ready (set `SENTRY_DSN`)
