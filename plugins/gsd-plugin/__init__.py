"""GSD Plugin — Official InkosAI extension for meta-prompting and phase-based development.

This plugin provides:
- Phase management commands
- Meta-prompt design capabilities
- Context engineering tools
- Quality validation integration
- Phase transition tracking

Example::

    from plugins.gsd_plugin import GSDPlugin

    plugin = GSDPlugin()
    await plugin.start_phase(
        phase="research",
        context={"task": "Investigate new approach"}
    )
"""

from __future__ import annotations

__version__ = "1.0.0"

from plugins.gsd_plugin.plugin import GSDPlugin

__all__ = ["GSDPlugin"]
