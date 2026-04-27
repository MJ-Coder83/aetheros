"""Gastown Plugin — Official InkosAI extension for workspace orchestration.

This plugin provides:
- Workspace initialization commands
- Agent coordination via Agent Bridge
- Session management integration
- Resource allocation capabilities
- Tape event logging

Example::

    from plugins.gastown_plugin import GastownPlugin

    plugin = GastownPlugin()
    await plugin.initialize_workspace(
        workspace_name="My Workspace",
        agent_pool_size=5
    )
"""

from __future__ import annotations

__version__ = "1.0.0"

from plugins.gastown_plugin.plugin import GastownPlugin

__all__ = ["GastownPlugin"]
