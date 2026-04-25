**Task**: Implement the full Domain Canvas with dual-mode support (Visual + Folder View).

Divide the work among 4 agents as follows (work in parallel, no blocking):

**Agent 1 – Canvas Core & Visual Engine**
- Create `packages/canvas/core.py` and `packages/canvas/models.py`
- Implement Canvas model, Node, Edge, LayoutEngine (supporting Layered, Hub-and-Spoke, Clustered, Linear, Smart Auto-Layout)
- Add synchronization logic between visual graph and folder-tree
- Add tests in `tests/test_canvas_core.py`

**Agent 2 – Browser Node & Universal Preview**
- Create `packages/canvas/nodes/browser.py`
- Implement BrowserNode that supports live embedding for web frameworks (React, Next.js, Vue, etc.), Electron, Tauri, Figma, and basic emulation for others
- Add element detection, tagging, and natural language editing support
- Add tests in `tests/test_browser_node.py`

**Agent 3 – Terminal Node & TUI Support**
- Create `packages/canvas/nodes/terminal.py`
- Implement TerminalNode with Visual TUI Layout Editor, AI co-pilot for layout suggestions, two-way sync (visual ↔ code)
- Support Go (Bubble Tea), Rust (Ratatui), Python (Textual), etc.
- Add tests in `tests/test_terminal_node.py`

**Agent 4 – Canvas UI Integration & Prime Features**
- Update the Prime Console UI (`apps/web`) to include the new Domain Canvas page (`/canvas`)
- Add dual-mode toggle (Visual ↔ Folder View)
- Integrate with existing Prime features (Folder Thinking Mode, Simulation, Explainability, Proposals)
- Update Living Spec with Domain Canvas section
- Run final `make lint`, `make typecheck`, `make test` for backend + `npm run build` for web

**Requirements for All Agents**:
- Keep everything backward-compatible
- Use existing folder_tree service for synchronization
- Log all canvas operations to Tape
- Commit message for each: `feat: implement Domain Canvas (part X/4)`

After all 4 agents finish, merge the changes cleanly and push to main.
