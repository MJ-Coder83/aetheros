# Changelog

All notable changes to InkosAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2025-04-27

### Added - Core Platform

#### Authentication & Security
- JWT-based authentication with access and refresh tokens
- Password hashing with bcrypt
- Role-based access control (RBAC) with admin/operator/viewer roles
- Token revocation support
- Refresh token rotation
- Secure password policy enforcement (8+ chars)
- Inactive user account deactivation

#### Production Readiness Phase 1 - Core Infrastructure
- Production-ready Docker configuration with multi-stage builds
- Docker Compose with PostgreSQL, Redis, API server support
- Non-root container execution (`inkosai` user)
- Health check endpoints integrated with Docker
- GitHub Actions CI/CD pipeline
- Security scanning (Trivy, Bandit)
- Rate limiting middleware (120 req/60sec)
- Request ID propagation middleware

#### Production Readiness Phase 2 - Observability
- OpenTelemetry tracing with FastAPI instrumentation
- Structured JSON logging with structlog
- Correlation ID propagation across services
- Prometheus metrics endpoint (`/api/metrics`)
- Business metrics: domains, swarms, plugins, canvas operations
- Health check framework with detailed status
- Kubernetes probes: liveness (`/api/live`), readiness (`/api/ready`)
- Distributed tracing export to Jaeger

#### Production Readiness Phase 3 - Final Hardening
- Security headers middleware (CSP, HSTS, X-Frame-Options)
- Request size limiting (10MB default)
- Comprehensive security headers on all responses

### Added - Core Abstractions

#### AetherGit
- Unique versioning system for agent workflows
- Commit creation with parent references
- Branch management with mapping
- Rewind capability for rollbacks
- Sandbox merge simulation
- Graph visualization of commit history

#### Tape
- Immutable append-only event log
- Semantic search with vector similarity
- Natural language query with AetherCommit integration
- Ensemble retrieval with re-ranking
- Structured event storage with JSON payloads
- Event type filtering and time-range queries

#### Prime
- Meta-agent with system-wide awareness
- Folder Thinking Mode for filesystem reasoning
- Introspection capabilities with self-modification proposals
- Multi-domain coordination for cross-domain features
- Suite execution with retry logic
- Knowledge synthesis from Tape

### Added - Visual Development

#### Domain Canvas
- Visual node-based editor with real-time sync
- Dual-mode interface (Visual ↔ Folder Tree)
- Browser Node with live element detection
- Terminal Node with TUI layout editor
- Plugin Node for marketplace integration
- Natural Language Canvas Editing
- Smart auto-layout with beautify
- Simulation overlay with real-time metrics
- Tape overlay for live event visualization

#### Nodes
- **Browser Node**: Live preview, element detection, NL editing
- **Terminal Node**: TUI layout, AI co-pilot integration
- **Plugin Node**: First-class marketplace integration
- **Code Editor Node**: Syntax highlighting, Prime suggestions
- **Database Node**: Schema visualization, query builder
- **Annotation Node**: Comments, requirements, decisions

### Added - Agent Orchestration

#### Swarm Mode
- **Quick Swarm**: Fast, conversational multi-agent execution
- **Governed Swarm**: Structured, auditable with AetherGit integration
- Multi-domain coordination across domain boundaries
- Real-time streaming results
- Agent role specialization (frontend, backend, database, etc.)

#### Planning Domains
- Structured multi-agent collaboration
- Workflow types: Collaborative, Sequential, Debate
- Consensus tracking with visualization
- Multi-step planning with checkpoints
- Bias detection in debates
- Full Tape integration for audit trail

### Added - Plugin System

#### Plugin Marketplace
- Plugin discovery and installation
- Version management and rollback
- Security analysis before installation
- Plugin execution via Deno sandbox
- Network whitelist enforcement
- Filesystem restrictions (`/tmp/sandbox`)
- Execution timeout (30s default)
- Memory limits (512MB default)

### Added - Testing & Quality

- 2100+ unit and integration tests
- Stabilization regression test suite
- Coverage for core packages and API routes
- Pyright type checking integration
- Ruff linting and formatting
- Continuous integration via GitHub Actions

### Documentation

- **README.md**: Quick start and tech stack overview
- **docs/LIVING_SPEC.md**: Living architectural specification
- **docs/DEPLOYMENT.md**: Production deployment guide
- **docs/API.md**: Complete API reference
- **docs/USER_GUIDE.md**: Comprehensive user documentation
- **CHANGELOG.md**: This file

### Changed

- Optimized database queries with proper indexing
- Enhanced error handling with structured responses
- Improved Prime response generation with prompt engineering

### Security

- All API endpoints secured with JWT authentication (except public health checks)
- Plugin sandbox isolation with Deno runtime
- Secure cookie handling in production mode
- Content Security Policy headers
- Rate limiting on all authenticated endpoints
- Input validation via Pydantic v2 schemas

## Known Issues

- Plugin sandbox requires udev rules for /dev/uinput permissions
- First-time setup requires manual JWT_SECRET_KEY generation
- Prometheus/Grafana volumes require manual cleanup for fresh install

## Roadmap

### 0.2.0 (Planned)
- WebSocket real-time updates
- Advanced collaborative editing
- Plugin SDK v2 with UI components
- Mobile app (React Native)

### 0.3.0 (Planned)
- Multi-cluster distributed deployment
- Advanced observability with custom dashboards
- AI-generated test suite from specifications
- Integration marketplace for external services

---

[0.1.0]: https://github.com/inkosai/inkosai/releases/tag/v0.1.0
