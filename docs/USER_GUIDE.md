# InkosAI User Guide

Complete guide to using InkosAI for visual AI-powered development.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Domain Creation](#domain-creation)
3. [Canvas](#canvas)
4. [Swarm Mode](#swarm-mode)
5. [Planning Domains](#planning-domains)
6. [Plugins](#plugins)
7. [Prime Assistant](#prime-assistant)
8. [Tips & Best Practices](#tips--best-practices)

## Getting Started

### First Login

```
URL: http://localhost:3000 (Web UI)
API: http://localhost:8000/api

Default admin credentials:
Username: admin
Password: (set in .env during setup)
```

### Quick Tour

1. **Dashboard** - Overview of domains, active swarms, and Tape events
2. **Canvas** - Visual domain builder with nodes and edges
3. **Tape** - Immutable audit log of all actions
4. **Prime** - AI assistant that understands the entire system

## Domain Creation

### One-Click Domain

The easiest way to start:

1. Click **"New Domain"** on the dashboard
2. Choose a template:
   - **Starter** - Empty domain with basic structure
   - **Web Application** - Frontend + backend scaffold
   - **Data Pipeline** - ETL pipeline nodes
   - **API Service** - REST API template
3. Enter a name and description
4. Click **Create**

### Custom Domain

For more control:

1. Click **"New Domain"** → **"Custom"**
2. Configure:
   - **Name**: Human-readable name
   - **Type**: Select or define domain type
   - **Folder Path**: Where domain files live (auto-generated)
3. Add starter nodes:
   - Browser Node (live preview)
   - Terminal Node (TUI editor)
   - Code Editor Node
   - Database Node

### Domain Templates

| Template | Best For | Pre-loaded With |
|----------|----------|-----------------|
| Web App | Frontend projects | Browser node, Component scaffold |
| Data Pipeline | ETL workflows | Transform nodes, Schedule nodes |
| API Service | Backend APIs | Route nodes, DB nodes |
| AI Application | LLM projects | Prime integration, Prompt nodes |

### Domain Settings

Access via Canvas → Settings gear:

- **Visibility**: Private / Shared / Public
- **Auto-save**: On/off (saves to AetherGit)
- **Prime Co-Pilot**: Enable AI suggestions
- **Swarm Mode**: Quick vs Governed

## Canvas

### Canvas Overview

The Canvas is a visual development environment with:
- **Nodes**: Components (Browser, Terminal, Code, Database, etc.)
- **Edges**: Connections between nodes
- **Simulations**: Run and test in real-time
- **Tape Overlay**: See system events live

### Node Types

#### Browser Node
Live web preview with AI editing:

```
1. Drag Browser Node onto canvas
2. Enter URL or start with blank
3. Click "Detect Elements" - Prime finds interactive elements
4. Use natural language: "Add a login button below the header"
5. See live preview update
```

**Features:**
- Live element detection
- Natural language editing
- Component library access
- Responsive preview modes

#### Terminal Node
TUI-based editing with Prime:

```
1. Drag Terminal Node onto canvas
2. Select layout (Split, Grid, Focus)
3. Start editing with Prime assistance
4. "Create a file upload component"
```

**Features:**
- Layout templates
- AI-powered code suggestions
- Terminal capabilities
- File explorer integration

#### Plugin Node
Integrate plugins directly:

```
1. Drag Plugin Node onto canvas
2. Select plugin from marketplace
3. Configure inputs/outputs
4. Connect to other nodes
```

### Canvas Operations

#### Creating Nodes

- **Click toolbar** → Select node type
- **Right-click canvas** → Quick insert
- **Prime command**: "Create a database node for users"

#### Connecting Nodes

1. Hover over node → Port appears
2. Drag from output to input
3. Edge auto-routes (or Prime optimizes)

#### Layout & Beautify

**Auto Layout:**
- Click **Beautify** button
- Choose layout: Grid, Hierarchical, Force-directed
- Prime automatically optimizes

**Natural Language Editing:**
```
"Move all database nodes to the right"
"Arrange these nodes into a pipeline flow"
"Group these nodes as 'Authentication'"
"Auto-layout the entire canvas"
```

### Simulation Mode

Test your Canvas in real-time:

1. Click **Simulation** toggle
2. Selected nodes run live:
   - Browser Node: Live URL fetching
   - Code Node: Code execution
   - Plugin Node: Plugin execution
3. See metrics overlaid on each node:
   - Execution time (ms)
   - Success/error count
   - Throughput (req/s)

#### Simulation Examples

```
"Simulate this form submission 100 times"
"Test this API endpoint with random data"
"Check for race conditions in this workflow"
```

### Canvas ↔ Folder Tree

The Canvas has a dual representation:

**Visual Mode** (Canvas):
- Best for: Humans, Prime, collaborative editing
- See live: events, simulations, Prime overlays

**Folder Mode** (Tree):
- Best for: Version control, git operations, agents
- Source of truth with deterministic structure

**Toggle:**
- Click **Folder Icon** in toolbar
- Changes reflect instantly both ways

## Swarm Mode

### Quick Swarm

For fast, iterative development:

```
1. Select nodes → Click "Swarm" or press Cmd+K
2. Describe task: "Implement user authentication"
3. Agents (frontend, backend) collaborate in real-time
4. Watch results appear in Terminal/Browser nodes
5. Iterate: "Add password validation"
```

**Characteristics:**
- Fast, conversational style
- Multiple agents work in parallel
- Results stream live
- Great for prototyping

### Governed Swarm

For structured, auditable changes:

```
1. Click "Governed Swarm" → Define scope
2. Statement: "Add user authentication system"
3. Prime analyzes → Creates proposal
4. Review proposal in Canvas:
   - Affected files highlighted
   - Impact analysis shown
   - AetherGit diff preview
5. Accept → Agents execute with AetherGit commits
6. Rollback button if issues
```

**Characteristics:**
- One proposal at a time
- Structured debate and review
- AetherGit versions every change
- Full traceability via Tape
- Prime validates and coordinates

### Multi-Domain Swarm

Work across multiple domains:

```
1. Select multiple domains from dashboard
2. Click "Multi-Domain Swarm"
3. Define coordination task:
   "Create shared authentication service " +
   "used by both web and mobile domains"
4. Agents coordinate across domains
5. Result: synchronized changes
```

**Use Cases:**
- Cross-domain features
- Shared libraries/components
- API contract updates
- Breaking change migrations

## Planning Domains

### What Are Planning Domains?

Structured coordination for multi-agent collaboration:

- **Agents**: Participants from different domains
- **Workflows**: Structured processes (debate, sequential, etc.)
- **Consensus**: Track decisions and votes
- **Traceability**: All discussions logged to Tape

### Creating a Planning Domain

```
1. Dashboard → "New Planning Domain"
2. Invite agents:
   - frontend@web-domain
   - backend@api-domain
   - database@data-domain
3. Select workflow:
   - Collaborative (simultaneous)
   - Sequential (taking turns)
   - Debate (structured argument)
4. Define objective and constraints
```

### Running a Planning Session

```
1. Define objective:
   "Design new payment system architecture"

2. Agents contribute asynchronously:
   - Add proposals
   - Comment on others
   - Refine solutions

3. Consensus tracking:
   - Votes on proposals
   - Visualization of agreement
   - Bias detection alerts

4. Prime coordinates:
   - Ensures structured flow
   - Synthesizes final design
   - Creates AetherGit commit
```

### Multi-Step Planning Example

```
Objective: Redesign checkout flow

Step 1 (Day 1): Current state analysis
- frontend shows current UX
- backend shows API limitations
- data shows conversion metrics

Step 2 (Day 2): Proposal round
- Each agent proposes improvements
- Prime clusters similar ideas

Step 3 (Day 3): Refinement
- Combine best proposals
- Identify dependencies

Step 4 (Day 4): Finalization
- Final architecture
- Rollout plan
- AetherGit commit created
```

## Plugins

### Plugin Marketplace

```
Marketplace → Browse plugins:
- Filter by category
- Sort by rating/downloads
- See Prime compatibility badge
- Preview before install
```

### Installing Plugins

```
1. Find plugin in Marketplace
2. Click "Install"
3. Prime analyzes security:
   - Permission analysis
   - Dependency check
   - Code review summary
4. Confirm installation
5. Plugin appears in node palette
```

### Creating Plugins

```javascript
// my-plugin.js
export async function run(sandbox) {
  const { input, fetch, fs } = sandbox;

  // Read from input
  const task = input.task;

  // Make restricted HTTP calls
  const response = await fetch('https://api.example.com/data');

  // File operations (in /tmp/sandbox only)
  await fs.writeTextFile('/tmp/sandbox/result.json', JSON.stringify(data));

  // Return result
  return { transformed: true, data };
}
```

**Plugin manifest** (`plugin.json`):
```json
{
  "id": "my-transform",
  "name": "Data Transformer",
  "version": "1.0.0",
  "permissions": [
    "network:api.example.com",
    "fs:read-write:/tmp/sandbox"
  ],
  "input_schema": {
    "task": "string"
  },
  "output_schema": {
    "transformed": "boolean",
    "data": "object"
  }
}
```

### Plugin Security

**Sandbox modes:**
- `disabled`: No plugin execution
- `deno`: Semi-isolated (timeout, memory limits)
- `docker`: Full container isolation

**Best Practices:**
- Review permissions before installing
- Use specific, minimal permissions
- Monitor plugin executions in Tape
- Unsused plugins: disable, don't uninstall (keep audit trail)

## Prime Assistant

### What is Prime?

Your AI partner that understands the entire InkosAI system:
- System state (Canvas, Tape, Domains)
- Your style and preferences
- Multi-modal (chat, Canvas, Terminal)
- Can propose and execute changes

### Chat Mode

**Basic conversation:**
```
"Help me create a new domain"
"What's the status of my active swarms?"
"Show me recent errors in the Tape"
```

**Action-oriented:**
```
"Create a Canvas node for user authentication"
"Generate a plan for adding dark mode"
"Start a Quick Swarm for this form validation"
```

**Context-aware:**
```
(selected nodes in Canvas)
"Refactor these three nodes into a service"
```

### Prime in Canvas

Prime appears as an overlay:

**Suggestions:**
- "Layout could be improved - would you like me to beautify?"
- "This code pattern looks inefficient - shall I optimize?"

**Execution:**
- "I'm creating the connection edge for you"
- "Starting simulation now..."

**Co-Pilot Mode:**
- Continuous suggestions
- UX issue detection (nested nodes, unreachable UI)
- Layout optimized for workflows
- Creates experiment branches (A/B tests)

### Prime in Terminal

```
$ prime "Create a React component for this form"

Prime: I'll create a responsive form component.
[Generates code with your preferred patterns]

$ prime "What dependencies am I missing?"

Prime: Checking package.json... You're missing axios.
```

### Prime Personalization

Prime learns from you:

```
1. Style preferences:
   - Code formatting
   - Design patterns
   - Naming conventions

2. Domain expertise:
   - Tech stack preferences
   - Architecture patterns
   - Tool preferences

3. Communication style:
   - Detail level
   - Response format
   - Tone preferences

4. Review checkpoints:
   - Approvals required for: deploys, breaking changes
   - Auto-approve: formatting, documentation
```

**Likes/Dislikes:**
```
Prime: "I've formatted this code."
You: (thumbs down)
Prime: "Got it - I'll keep the original formatting next time."
```

## Tips & Best Practices

### Domain Organization

**Recommended structure:**
```
domains/
├── user-facing/         # Customer features
├── internal-tools/      # Admin, analytics
├── shared-library/      # Reusable components
└── experiments/         # A/B tests, spikes
```

**Naming:**
- Descriptive: `user-authentication` not `auth`
- Hierarchical: `web/checkout/payment`
- Version: `api-v2` not `api-new`

### Canvas Hygiene

- **Group nodes**: Use containers for related functionality
- **Label edges**: What does this connection mean?
- **Color coding**: Consistent colors for node types
- **Regular beautify**: Prime's auto-layout is good
- **Simulate before commit**: Test in simulation mode

### AetherGit Workflow

```
1. Start feature: Prime creates asia/129-domain-canvas
2. Make changes: Each significant change is a commit
3. Review: Visual diff in Canvas
4. Merge: Prime proposes merge to main
5. Deploy: Production promotion with rollback button
```

### Swarm Efficiency

- **Quick Swarm**: Prototypes, experiments, UI tweaks
- **Governed Swarm**: Architecture decisions, API changes
- **Prime suggestions**: When Prime suggests a swarm, it's often worth trying

### Security Reminders

- Rotate JWT_SECRET_KEY regularly
- Review plugin permissions
- Monitor Tape for unusual activity
- Keep plugin sandbox mode on `docker` in production

### Getting Help

- **Prime**: Ask anything - it knows the whole system
- **Tape**: Search history for similar issues
- **Documentation**: See docs/ folder
- **Community**: Discord, GitHub discussions

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Domain | Cmd+Shift+N |
| Swarm Mode | Cmd+K |
| Beautify Canvas | Cmd+B |
| Toggle Simulation | Cmd+S |
| Toggle Folder View | Cmd+F |
| Prime Chat | Cmd+P |
| Save | Cmd+S |
| Undo | Cmd+Z |
| Redo | Cmd+Shift+Z |
