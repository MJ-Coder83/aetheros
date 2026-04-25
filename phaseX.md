**Task**: Implement the full Plugin System and Plugin Marketplace for InkosAI.

Divide the work among 4 agents as follows (work in parallel, no blocking):

**Agent 1 – Plugin Core & SDK**
- Create `packages/plugin/core.py` and `packages/plugin/models.py`
- Implement Plugin model, PluginManifest, PluginSandbox, PluginPermission system
- Create PluginSDK with register_plugin, load_plugin, execute_command, subscribe_to_events
- Add tests in `tests/test_plugin_core.py`

**Agent 2 – Plugin Runtime & Agent Bridge**
- Create `packages/plugin/bridge.py`
- Implement AgentBridge with secure command routing, permission checking, audit logging
- Add sandboxing and event bus for plugins
- Add tests in `tests/test_plugin_bridge.py`

**Agent 3 – Marketplace Backend**
- Create `packages/marketplace/service.py`
- Implement Plugin Marketplace with discovery, search, installation, rating, permission flow
- Add API endpoints in `services/api/routes/marketplace.py`
- Add tests in `tests/test_marketplace.py`

**Agent 4 – Marketplace UI & Prime Integration**
- Update Prime Console UI with Marketplace page (`/marketplace`)
- Add "Install Plugin" flow with permission UI
- Update Prime to discover and use installed plugins
- Update Living Spec with full Plugin System + Marketplace section
- Run final `make lint`, `make typecheck`, `make test`, and `npm run build`

**Requirements for All Agents**:
- Keep everything backward-compatible
- Use existing folder_tree and Tape services
- Log all plugin operations to Tape
- Commit message for each: `feat: implement Plugin System and Marketplace (part X/4)`

After all 4 agents finish, merge the changes cleanly and push to main.
