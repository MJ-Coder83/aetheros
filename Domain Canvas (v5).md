**Task**: Implement the full **Domain Canvas (v5)** — the central visual development environment of InkosAI.

**Goal**: Create a powerful, universal visual workspace where humans and Prime collaborate to build, connect, simulate, version, and evolve agent systems across any UI type (web, mobile, desktop, TUI, video, game engines, etc.). The canvas must feel like the best AI-native visual development environment ever built.

### Requirements

1. **Tiered UI Support** (implement Tier 1 first, with clear extension points for Tier 2–4):
   - Tier 1: Browser-Native (React, Next.js, Vue, Angular, Svelte, Electron, Tauri, Figma, Framer, Storybook)
   - Tier 2: High-Fidelity Emulation (Flutter, React Native, .NET MAUI, SwiftUI, WPF, Qt)
   - Tier 3: Terminal / TUI (Go Bubble Tea, Rust Ratatui, Python Textual)
   - Tier 4: Plugin Nodes (Godot, Blender, DaVinci Resolve, VS Code, proprietary tools)

2. **Dual-Mode Interface** (core feature):
   - **Visual Mode** — Node-based canvas with drag-and-drop, connections, live previews
   - **Folder Mode** — Tree/file explorer view synchronized with the visual graph
   - One-click toggle between modes; changes in one mode instantly update the other

3. **Key Node Types**:
   - **Browser Node** — Live interactive preview, element detection, tagging, natural language editing, two-way interaction
   - **Terminal Node** — Visual TUI layout editor + AI Co-Pilot for layout suggestions, natural language commands, two-way code ↔ visual sync
   - **Plugin Node** — First-class support for embedded tools via the Plugin SDK
   - Standard nodes (Agent, Skill, Crew, Data Source, Simulation, Debate, etc.)

4. **Core Capabilities**:
   - Smart Auto-Layout + Beautify button
   - Live Simulation Overlay with real-time metrics on every node
   - Tape Overlay showing live events flowing through the canvas
   - Natural Language Canvas Editing ("Make the CTA button larger and move it above the fold")
   - Prime Co-Pilot Mode (suggestions, UX issue detection, A/B variants, auto-optimizations)
   - Full AetherGit versioning with visual diff and rewind
   - Swarm integration (Quick Swarm and Governed Swarm buttons directly on the canvas, multi-domain support)

5. **Integration**:
   - Full folder-tree dual representation (source of truth)
   - Deep integration with Prime, Tape, AetherGit, Simulation Engine, Debate Arena, Skill Evolution, Explainability
   - Support for multi-domain swarms (agents from different domains working on the same canvas)
   - Solo-dev friendly (simple workflows, minimal clutter option, folder-first mode)

6. **UI/UX**:
   - Dark futuristic theme with glassmorphism, purple/cyan accents
   - Responsive, smooth animations, mini-map, search/filter
   - Real-time collaboration ready (multi-user cursors)

7. **Testing & Quality**:
   - Minimum 80 new tests in `tests/test_canvas.py`
   - Run full lint, typecheck, and test suite
   - Ensure backward compatibility with all existing features

**Commit Message**: `feat: implement full Domain Canvas (v5) with tiered UI support, dual-mode, Browser Node, Terminal Node, Plugin Nodes, swarm integration, and folder-tree dual representation`

Please implement this at the highest quality level with clean architecture, excellent UX, and full integration with existing systems.
