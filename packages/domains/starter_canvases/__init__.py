"""Starter Canvas Templates for Planning Domains.

This module provides pre-configured starter canvases for:
- Gastown Domain
- GSD Domain
- BMAD Domain
- Planning Super Domain

Each canvas includes:
- Visually organized nodes with domain-specific colors
- Dual-mode (Visual + Folder) support
- Quick Swarm and Governed Swarm buttons
- Proper node types and connections

Example::

    from packages.domains.starter_canvases import (
        GastownStarterCanvas,
        GSDStarterCanvas,
        BMADStarterCanvas,
        PlanningSuperStarterCanvas,
    )

    # Generate a starter canvas
    canvas = GastownStarterCanvas.generate()
"""

from __future__ import annotations

from packages.domains.starter_canvases.bmad import BMADStarterCanvas
from packages.domains.starter_canvases.gastown import GastownStarterCanvas
from packages.domains.starter_canvases.generator import PlanningStarterCanvasGenerator
from packages.domains.starter_canvases.gsd import GSDStarterCanvas
from packages.domains.starter_canvases.super_domain import PlanningSuperStarterCanvas

__all__ = [
    # Individual canvas generators
    "GastownStarterCanvas",
    "GSDStarterCanvas",
    "BMADStarterCanvas",
    "PlanningSuperStarterCanvas",
    # Generator factory
    "PlanningStarterCanvasGenerator",
]
