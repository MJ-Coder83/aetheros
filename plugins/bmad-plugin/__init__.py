"""BMAD Plugin — Official InkosAI extension for agile sprint planning and breakthrough facilitation.

This plugin provides:
- Sprint management commands
- Breakthrough session facilitation
- Track coordination tools
- Velocity tracking
- Sprint review capabilities

Example::

    from plugins.bmad_plugin import BMADPlugin

    plugin = BMADPlugin()
    await plugin.start_sprint(
        sprint_name="Sprint 1",
        goals=["Complete feature X", "Implement Y"],
        duration_days=14
    )
"""

from __future__ import annotations

__version__ = "1.0.0"

from plugins.bmad_plugin.plugin import BMADPlugin

__all__ = ["BMADPlugin"]
