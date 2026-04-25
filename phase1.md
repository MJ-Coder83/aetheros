**Task**: Fully integrate One-Click Domain Creation with the Domain Canvas (final step).

Divide the work among 4 agents as follows (work in parallel, no blocking):

**Agent 1 – Domain Creation + Canvas Integration**
- Update `packages/domain/creation.py` so `create_domain_from_description()` with `DOMAIN_WITH_STARTER_CANVAS` calls `StarterCanvasGenerator`
- Ensure the generated starter canvas uses the correct layout and is linked to the domain’s folder-tree
- Add tests for the full flow

**Agent 2 – Canvas Service Enhancements**
- Update `packages/canvas/core.py` and `packages/canvas/service.py` to support automatic creation from a DomainBlueprint
- Add `create_canvas_from_domain()` method with proper node/edge generation from blueprint
- Ensure folder-tree ↔ visual sync works on new canvases

**Agent 3 – Prime Integration & UX Flow**
- Update Prime to call the new domain creation flow when user requests a domain
- Add natural language handling in Prime Console for "Create domain X"
- Update Living Spec with the completed One-Click Domain Creation + Canvas integration section

**Agent 4 – API, UI & Final Polish**
- Add or update the `/domains/one-click` endpoint to return canvas_id when starter canvas is requested
- Update the Prime Console UI (`/canvas` page) to handle new domain creation flow with smooth UX
- Run full `make lint`, `make typecheck`, `make test`, and `npm run build`

**Requirements for All Agents**:
- Keep everything backward-compatible
- Use existing folder_tree and canvas services
- Log all operations to Tape
- Commit message for each: `feat: integrate One-Click Domain Creation with Domain Canvas (part X/4)`

After all 4 agents finish, merge the changes cleanly and push to main.
