**Task**: Implement One-Click Domain Creation with full folder-tree support.

Divide the work among 4 agents as follows (work in parallel, no blocking):

**Agent 1 – Domain Blueprint & Folder-Tree Generator**
- Create `packages/domain/domain_blueprint.py`
- Implement `DomainBlueprint` model (metadata, agents, skills, workflows, config, templates, data_sources, evaluation_criteria)
- Implement `DomainFolderTreeGenerator` that creates the clean folder-tree structure from a blueprint
- Add tests in `tests/test_domain_blueprint.py`

**Agent 2 – Domain Creation Engine & API**
- Create `packages/domain/creation.py`
- Implement `DomainCreationEngine` with `create_domain_from_description()` (natural language → blueprint + folder tree)
- Add two options: "Domain Only" and "Domain + Starter Canvas"
- Create API endpoints in `services/api/routes/domain.py`
- Add tests in `tests/test_domain_creation.py`

**Agent 3 – Starter Canvas Generation**
- Create `packages/domain/starter_canvas.py`
- Implement smart auto-layout (Layered, Hub-and-Spoke, Clustered, etc.)
- Generate a visual starter canvas with connected nodes when requested
- Integrate with existing Canvas system
- Add tests in `tests/test_starter_canvas.py`

**Agent 4 – Prime & Integration Layer**
- Update Prime to use folder-tree when creating domains
- Add Folder Thinking Mode calls in domain creation flow
- Update Living Spec with new feature section
- Ensure full integration with AetherGit, Tape, and existing systems
- Run final `make lint`, `make typecheck`, `make test`

**Requirements for All Agents**:
- Keep everything backward-compatible
- Use existing folder_tree service
- Log all operations to Tape
- Commit message for each: `feat: implement One-Click Domain Creation (part X/4)`

After all 4 agents finish, merge the changes cleanly and push to main.
