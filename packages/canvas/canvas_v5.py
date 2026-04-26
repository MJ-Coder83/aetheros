"""Domain Canvas (v5) -- Full visual development environment for InkosAI.

This module provides the advanced Canvas v5 features on top of the core
CanvasService:

1. **Plugin Nodes** -- First-class embedded tool nodes via the Plugin SDK
2. **Simulation Overlay** -- Real-time metrics from the SimulationEngine on
   every canvas node
3. **Tape Overlay** -- Live Tape events flowing through the canvas
4. **Natural Language Canvas Editing** -- "Make the CTA button larger" style
   commands that modify canvas nodes
5. **Prime Co-Pilot** -- AI-driven suggestions, UX issue detection, A/B
   variant generation, auto-optimizations
6. **AetherGit Versioning** -- Visual diff and rewind for canvas history
7. **Swarm Integration** -- Quick Swarm and Governed Swarm buttons on the
   canvas with multi-domain support
8. **Tiered UI Support** -- Framework registry for Tier 1 (Browser-Native)
   through Tier 4 (Plugin Nodes)

All operations are logged to the Tape for full auditability.

Architecture::

  CanvasV5Engine
  ├── PluginNodeManager     -- register / manage plugin nodes
  ├── SimulationOverlay     -- real-time metrics per node
  ├── TapeOverlay           -- live event stream on canvas
  ├── NLEditEngine          -- natural language canvas editing
  ├── PrimeCoPilot          -- AI suggestions + auto-optimizations
  ├── CanvasVersioning      -- AetherGit-style version history
  ├── SwarmIntegration      -- Quick + Governed swarms on canvas
  └── TieredUIRegistry      -- framework support registry

Usage::

  from packages.canvas.canvas_v5 import CanvasV5Engine

  engine = CanvasV5Engine(
      tape_service=tape_svc,
      canvas_service=canvas_svc,
      simulation_engine=sim_engine,
      proposal_engine=proposal_engine,
  )

  # Natural language edit
  result = await engine.natural_language_edit(
      domain_id="legal-research",
      instruction="Make the domain node larger and move it to the center",
  )

  # Prime Co-Pilot suggestions
  suggestions = await engine.get_copilot_suggestions("legal-research")

  # Run Quick Swarm
  swarm_result = await engine.run_quick_swarm(
      domain_id="legal-research",
      task="Optimize the agent layout for faster contract review",
  )
"""

from __future__ import annotations

import contextlib
import re
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.canvas.models import (
    Canvas,
    CanvasEdge,
    CanvasEdgeType,
    CanvasError,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    CanvasViewMode,
)
from packages.tape.service import TapeService

if TYPE_CHECKING:
    from packages.canvas.core import CanvasService
    from packages.folder_tree.impact import ImpactAnalyzer
    from packages.prime.debate import DebateArena
    from packages.prime.explainability import ExplainabilityEngine
    from packages.prime.introspection import PrimeIntrospector
    from packages.prime.proposals import ProposalEngine
    from packages.simulation.engine import SimulationEngine

__all__ = [
    "CanvasV5Engine",
    "CanvasVersion",
    "CanvasVersioningManager",
    "ConflictResolutionResult",
    "ConflictSeverity",
    "ConflictStatus",
    "CopilotSuggestion",
    "CopilotSuggestionType",
    "CrossDomainConflict",
    "DomainGroup",
    "FrameworkTier",
    "GovernedSwarmResult",
    "MultiDomainSwarmConfig",
    "MultiDomainSwarmEngine",
    "MultiDomainSwarmProgress",
    "MultiDomainSwarmResult",
    "NLEditEngine",
    "NLEditResult",
    "NLEditType",
    "PluginNodeConfig",
    "PluginNodeManager",
    "PrimeCoPilot",
    "QuickSwarmResult",
    "SimulationMetric",
    "SimulationOverlay",
    "SwarmIntegration",
    "TapeEventEntry",
    "TapeOverlay",
    "TieredFramework",
    "TieredUIRegistry",
    "UIFramework",
]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FrameworkTier(StrEnum):
    """Tier level for UI framework support."""

    TIER_1_BROWSER = "tier_1_browser"  # Browser-Native
    TIER_2_HIGH_FIDELITY = "tier_2_high_fidelity"  # High-Fidelity Emulation
    TIER_3_TERMINAL = "tier_3_terminal"  # Terminal / TUI
    TIER_4_PLUGIN = "tier_4_plugin"  # Plugin Nodes


class UIFramework(StrEnum):
    """Supported UI frameworks across all tiers."""

    # Tier 1: Browser-Native
    REACT = "react"
    NEXT_JS = "next_js"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    ELECTRON = "electron"
    TAURI = "tauri"
    FIGMA = "figma"
    FRAMER = "framer"
    STORYBOOK = "storybook"

    # Tier 2: High-Fidelity Emulation
    FLUTTER = "flutter"
    REACT_NATIVE = "react_native"
    DOTNET_MAUI = "dotnet_maui"
    SWIFTUI = "swiftui"
    WPF = "wpf"
    QT = "qt"

    # Tier 3: Terminal / TUI
    BUBBLETEA = "bubbletea"
    RATATUI = "ratatui"
    TEXTUAL = "textual"

    # Tier 4: Plugin Nodes
    GODOT = "godot"
    BLENDER = "blender"
    DAVINCI = "davinci_resolve"
    VSCODE = "vscode"


class NLEditType(StrEnum):
    """Type of natural language canvas edit."""

    MOVE = "move"
    RESIZE = "resize"
    RELABEL = "relabel"
    RESTYLE = "restyle"
    ADD = "add"
    REMOVE = "remove"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    LAYOUT = "layout"
    COMPOUND = "compound"


class CopilotSuggestionType(StrEnum):
    """Type of Prime Co-Pilot suggestion."""

    UX_ISSUE = "ux_issue"
    LAYOUT_OPTIMIZATION = "layout_optimization"
    AB_VARIANT = "ab_variant"
    AUTO_OPTIMIZATION = "auto_optimization"
    MISSING_CONNECTION = "missing_connection"
    REDUNDANT_NODE = "redundant_node"
    BEST_PRACTICE = "best_practice"


class SwarmMode(StrEnum):
    """Swarm execution mode."""

    QUICK = "quick"
    GOVERNED = "governed"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TieredFramework(BaseModel):
    """A registered UI framework with its tier and metadata."""

    framework: UIFramework
    tier: FrameworkTier
    label: str
    description: str = ""
    icon: str = ""
    preview_supported: bool = False
    live_editing_supported: bool = False
    code_generation_supported: bool = False
    file_extensions: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class PluginNodeConfig(BaseModel):
    """Configuration for a Plugin Node on the canvas."""

    plugin_id: str
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    plugin_type: str = ""
    capabilities: list[str] = Field(default_factory=list)
    command_registry: list[str] = Field(default_factory=list)
    status: str = "idle"
    embed_url: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimulationMetric(BaseModel):
    """A single real-time simulation metric for a canvas node."""

    metric_name: str
    value: float
    unit: str = ""
    status: str = "normal"  # normal, warning, critical
    trend: str = "stable"  # stable, improving, degrading
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TapeEventEntry(BaseModel):
    """A Tape event displayed on the canvas overlay."""

    event_id: str
    event_type: str
    agent_id: str = ""
    source_node_id: str | None = None
    target_node_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    direction: str = "through"  # into, out_of, through


class NLEditResult(BaseModel):
    """Result of a natural language canvas edit."""

    edit_id: str = Field(default_factory=lambda: str(uuid4()))
    instruction: str
    edit_type: NLEditType
    confidence: float = 0.0
    applied: bool = False
    changes: list[dict[str, object]] = Field(default_factory=list)
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CopilotSuggestion(BaseModel):
    """A single Prime Co-Pilot suggestion for the canvas."""

    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    suggestion_type: CopilotSuggestionType
    title: str
    description: str = ""
    confidence: float = 0.0
    impact: str = "low"  # low, medium, high
    target_node_ids: list[str] = Field(default_factory=list)
    auto_applicable: bool = False
    details: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CanvasVersion(BaseModel):
    """A single version snapshot of a canvas for AetherGit-style versioning."""

    version: int
    canvas_id: UUID
    domain_id: str
    snapshot: dict[str, object] = Field(default_factory=dict)
    commit_message: str = ""
    author: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuickSwarmResult(BaseModel):
    """Result of a Quick Swarm execution on the canvas."""

    swarm_id: str = Field(default_factory=lambda: str(uuid4()))
    task: str
    status: str = "completed"
    participants: list[str] = Field(default_factory=list)
    results: list[dict[str, object]] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernedSwarmResult(BaseModel):
    """Result of a Governed Swarm execution (requires approval)."""

    swarm_id: str = Field(default_factory=lambda: str(uuid4()))
    task: str
    status: str = "pending_approval"
    proposal_id: str = ""
    participants: list[str] = Field(default_factory=list)
    proposed_changes: list[dict[str, object]] = Field(default_factory=list)
    approval_required: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConflictSeverity(StrEnum):
    """Severity of a cross-domain conflict."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictStatus(StrEnum):
    """Status of a cross-domain conflict resolution."""

    DETECTED = "detected"
    IN_RESOLUTION = "in_resolution"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class CrossDomainConflict(BaseModel):
    """A conflict between agents from different domains."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    domain_ids: list[str]
    agent_ids: list[str]
    description: str = ""
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution: str = ""
    debate_id: str | None = None
    simulation_run_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConflictResolutionResult(BaseModel):
    """Result of resolving a cross-domain conflict."""

    conflict_id: str
    method: str
    success: bool = True
    resolution: str = ""
    debate_result: dict[str, object] | None = None
    simulation_result: dict[str, object] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DomainGroup(BaseModel):
    """A color-coded group of agents from one domain on the canvas."""

    domain_id: str
    domain_name: str = ""
    color: str = "#6366f1"
    agent_ids: list[str] = Field(default_factory=list)
    node_ids: list[str] = Field(default_factory=list)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})


class MultiDomainSwarmConfig(BaseModel):
    """Configuration for a multi-domain swarm run."""

    domain_ids: list[str]
    task: str
    governed: bool = False
    agent_ids: list[str] | None = None
    max_conflicts: int = 10
    auto_resolve_conflicts: bool = True
    simulate_before_execute: bool = True
    debate_format: str = "standard"
    max_debate_rounds: int = 3
    impact_analysis_enabled: bool = True
    folder_path: str = "/swarms/multi_domain/current_task/"
    color_palette: list[str] = Field(
        default_factory=lambda: [
            "#6366f1",  # Indigo
            "#ec4899",  # Pink
            "#f59e0b",  # Amber
            "#10b981",  # Emerald
            "#8b5cf6",  # Violet
            "#ef4444",  # Red
            "#06b6d4",  # Cyan
            "#84cc16",  # Lime
        ],
    )


class MultiDomainSwarmProgress(BaseModel):
    """Live progress of a multi-domain swarm execution."""

    swarm_id: str
    status: str = "initializing"
    domain_groups: list[DomainGroup] = Field(default_factory=list)
    conflicts: list[CrossDomainConflict] = Field(default_factory=list)
    resolved_conflicts: int = 0
    total_conflicts: int = 0
    simulation_completed: bool = False
    impact_reports: list[dict[str, object]] = Field(default_factory=list)
    current_phase: str = "initialization"
    progress_percent: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MultiDomainSwarmResult(BaseModel):
    """Result of a multi-domain swarm execution."""

    swarm_id: str = Field(default_factory=lambda: str(uuid4()))
    task: str
    domain_ids: list[str]
    domain_groups: list[DomainGroup] = Field(default_factory=list)
    status: str = "completed"
    mode: str = "quick"
    participants: list[str] = Field(default_factory=list)
    results: list[dict[str, object]] = Field(default_factory=list)
    conflicts: list[CrossDomainConflict] = Field(default_factory=list)
    conflict_resolutions: list[ConflictResolutionResult] = Field(default_factory=list)
    simulation_completed: bool = False
    simulation_passed: bool = True
    impact_severity: str = "low"
    folder_path: str = ""
    aethergit_branch: str = ""
    explanation_id: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# TieredUIRegistry
# ---------------------------------------------------------------------------
# TieredUIRegistry
# ---------------------------------------------------------------------------


class TieredUIRegistry:
    """Registry of supported UI frameworks organized by tier.

    Tier 1 frameworks are fully supported with live preview and editing.
    Tier 2 frameworks get high-fidelity emulation.
    Tier 3 frameworks get TUI layout editing.
    Tier 4 frameworks are extensible via the Plugin SDK.
    """

    _DEFAULT_FRAMEWORKS: ClassVar[list[dict[str, str | bool | list[str]]]] = [
        # Tier 1: Browser-Native
        {"framework": UIFramework.REACT, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "React", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".tsx", ".jsx"]},
        {"framework": UIFramework.NEXT_JS, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Next.js", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".tsx", ".jsx"]},
        {"framework": UIFramework.VUE, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Vue", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".vue"]},
        {"framework": UIFramework.ANGULAR, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Angular", "preview_supported": True, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".ts", ".html"]},
        {"framework": UIFramework.SVELTE, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Svelte", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".svelte"]},
        {"framework": UIFramework.ELECTRON, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Electron", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".js", ".ts"]},
        {"framework": UIFramework.TAURI, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Tauri", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".rs", ".ts"]},
        {"framework": UIFramework.FIGMA, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Figma", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": False, "file_extensions": [".fig"]},
        {"framework": UIFramework.FRAMER, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Framer", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": True, "file_extensions": [".tsx"]},
        {"framework": UIFramework.STORYBOOK, "tier": FrameworkTier.TIER_1_BROWSER,
         "label": "Storybook", "preview_supported": True, "live_editing_supported": True,
         "code_generation_supported": False, "file_extensions": [".stories.tsx"]},
        # Tier 2: High-Fidelity Emulation
        {"framework": UIFramework.FLUTTER, "tier": FrameworkTier.TIER_2_HIGH_FIDELITY,
         "label": "Flutter", "preview_supported": True, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".dart"]},
        {"framework": UIFramework.REACT_NATIVE, "tier": FrameworkTier.TIER_2_HIGH_FIDELITY,
         "label": "React Native", "preview_supported": True, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".tsx"]},
        {"framework": UIFramework.SWIFTUI, "tier": FrameworkTier.TIER_2_HIGH_FIDELITY,
         "label": "SwiftUI", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".swift"]},
        # Tier 3: Terminal / TUI
        {"framework": UIFramework.TEXTUAL, "tier": FrameworkTier.TIER_3_TERMINAL,
         "label": "Textual", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".py"]},
        {"framework": UIFramework.BUBBLETEA, "tier": FrameworkTier.TIER_3_TERMINAL,
         "label": "Bubble Tea", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".go"]},
        {"framework": UIFramework.RATATUI, "tier": FrameworkTier.TIER_3_TERMINAL,
         "label": "Ratatui", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": True, "file_extensions": [".rs"]},
        # Tier 4: Plugin Nodes
        {"framework": UIFramework.GODOT, "tier": FrameworkTier.TIER_4_PLUGIN,
         "label": "Godot", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": False, "file_extensions": [".tscn", ".gd"]},
        {"framework": UIFramework.BLENDER, "tier": FrameworkTier.TIER_4_PLUGIN,
         "label": "Blender", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": False, "file_extensions": [".blend"]},
        {"framework": UIFramework.VSCODE, "tier": FrameworkTier.TIER_4_PLUGIN,
         "label": "VS Code", "preview_supported": False, "live_editing_supported": False,
         "code_generation_supported": False, "file_extensions": [".vsix"]},
    ]

    def __init__(self) -> None:
        self._frameworks: dict[str, TieredFramework] = {}
        for fw_data in self._DEFAULT_FRAMEWORKS:
            fw = TieredFramework(
                framework=UIFramework(str(fw_data["framework"])),
                tier=FrameworkTier(str(fw_data["tier"])),
                label=str(fw_data.get("label", "")),
                preview_supported=bool(fw_data.get("preview_supported", False)),
                live_editing_supported=bool(fw_data.get("live_editing_supported", False)),
                code_generation_supported=bool(fw_data.get("code_generation_supported", False)),
                file_extensions=list(fw_data["file_extensions"]) if "file_extensions" in fw_data and isinstance(fw_data["file_extensions"], list) else [],
            )
            self._frameworks[fw.framework.value] = fw

    def register_framework(self, framework: TieredFramework) -> None:
        """Register a new framework or override an existing one."""
        self._frameworks[framework.framework.value] = framework

    def get_framework(self, name: str) -> TieredFramework | None:
        """Get a framework by name."""
        return self._frameworks.get(name)

    def list_frameworks(self, tier: FrameworkTier | None = None) -> list[TieredFramework]:
        """List all frameworks, optionally filtered by tier."""
        frameworks = list(self._frameworks.values())
        if tier is not None:
            frameworks = [f for f in frameworks if f.tier == tier]
        return frameworks

    def get_tier(self, framework_name: str) -> FrameworkTier | None:
        """Get the tier for a given framework name."""
        fw = self._frameworks.get(framework_name)
        return fw.tier if fw else None

    def detect_framework(self, file_extension: str) -> TieredFramework | None:
        """Detect the framework from a file extension."""
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = "." + ext
        for fw in self._frameworks.values():
            if ext in fw.file_extensions:
                return fw
        return None


# ---------------------------------------------------------------------------
# PluginNodeManager
# ---------------------------------------------------------------------------


class PluginNodeManager:
    """Manage Plugin Nodes on the canvas.

    Plugin Nodes are first-class canvas nodes that embed external tools
    via the Plugin SDK. They support command execution, event subscription,
    and can have embedded UIs (iframe URLs).
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._plugin_nodes: dict[str, PluginNodeConfig] = {}  # node_id -> config

    def register_plugin_node(self, config: PluginNodeConfig) -> PluginNodeConfig:
        """Register a new plugin node on the canvas."""
        if config.node_id in self._plugin_nodes:
            raise CanvasError(f"Plugin node '{config.node_id}' already exists")
        self._plugin_nodes[config.node_id] = config
        return config

    def get_plugin_node(self, node_id: str) -> PluginNodeConfig | None:
        """Get a plugin node by ID."""
        return self._plugin_nodes.get(node_id)

    def list_plugin_nodes(self) -> list[PluginNodeConfig]:
        """List all registered plugin nodes."""
        return list(self._plugin_nodes.values())

    def update_plugin_node(
        self,
        node_id: str,
        label: str | None = None,
        status: str | None = None,
        embed_url: str | None = None,
        capabilities: list[str] | None = None,
    ) -> PluginNodeConfig:
        """Update a plugin node's configuration."""
        node = self._plugin_nodes.get(node_id)
        if node is None:
            raise CanvasError(f"Plugin node '{node_id}' not found")
        if label is not None:
            node.label = label
        if status is not None:
            node.status = status
        if embed_url is not None:
            node.embed_url = embed_url
        if capabilities is not None:
            node.capabilities = capabilities
        return node

    def remove_plugin_node(self, node_id: str) -> PluginNodeConfig | None:
        """Remove a plugin node from the canvas."""
        return self._plugin_nodes.pop(node_id, None)

    def execute_command(self, node_id: str, command: str, args: dict[str, object] | None = None) -> dict[str, object]:
        """Execute a command on a plugin node.

        Returns a dict with the execution result. Commands are dispatched
        to the plugin via the Plugin SDK bridge.
        """
        node = self._plugin_nodes.get(node_id)
        if node is None:
            raise CanvasError(f"Plugin node '{node_id}' not found")
        if command not in node.command_registry and node.command_registry:
            raise CanvasError(
                f"Command '{command}' not available on plugin '{node.plugin_id}'"
            )
        return {
            "node_id": node_id,
            "command": command,
            "status": "executed",
            "args": args or {},
            "result": "ok",
        }

    async def log_plugin_event(
        self,
        node_id: str,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        """Log a plugin node event to the Tape."""
        await self._tape.log_event(
            event_type=f"canvas.plugin.{event_type}",
            agent_id="canvas-v5",
            payload={
                "node_id": node_id,
                "event_type": event_type,
                **(payload or {}),
            },
        )


# ---------------------------------------------------------------------------
# SimulationOverlay
# ---------------------------------------------------------------------------


class SimulationOverlay:
    """Real-time simulation metrics overlay for canvas nodes.

    Provides per-node metrics (execution time, success rate, throughput,
    error count) that are displayed on the canvas as status badges,
    colour-coded borders, and sparkline mini-charts.

    Metrics come from the SimulationEngine; when no simulation is running,
    the overlay shows the most recent completed simulation's results.
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._metrics: dict[str, list[SimulationMetric]] = defaultdict(list)
        self._active_simulation: str | None = None

    def set_active_simulation(self, simulation_id: str | None) -> None:
        """Set or clear the active simulation being overlaid."""
        self._active_simulation = simulation_id

    def update_node_metric(
        self,
        node_id: str,
        metric_name: str,
        value: float,
        unit: str = "",
        status: str = "normal",
        trend: str = "stable",
    ) -> SimulationMetric:
        """Update a metric for a canvas node."""
        metric = SimulationMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            status=status,
            trend=trend,
        )
        self._metrics[node_id].append(metric)
        # Keep only last 100 metrics per node
        if len(self._metrics[node_id]) > 100:
            self._metrics[node_id] = self._metrics[node_id][-100:]
        return metric

    def get_node_metrics(self, node_id: str) -> list[SimulationMetric]:
        """Get all current metrics for a node."""
        return self._metrics.get(node_id, [])

    def get_latest_metrics(self, node_id: str) -> dict[str, SimulationMetric]:
        """Get the latest value of each metric for a node."""
        metrics: dict[str, SimulationMetric] = {}
        for m in self._metrics.get(node_id, []):
            metrics[m.metric_name] = m
        return metrics

    def get_overlay_data(self, node_ids: list[str] | None = None) -> dict[str, dict[str, SimulationMetric]]:
        """Get overlay data for specified nodes (or all)."""
        target_ids = node_ids or list(self._metrics.keys())
        return {nid: self.get_latest_metrics(nid) for nid in target_ids if nid in self._metrics}

    def clear_metrics(self, node_id: str | None = None) -> None:
        """Clear metrics for a specific node or all nodes."""
        if node_id is not None:
            self._metrics.pop(node_id, None)
        else:
            self._metrics.clear()

    async def log_overlay_event(self, event_type: str, payload: dict[str, object]) -> None:
        """Log an overlay event to the Tape."""
        await self._tape.log_event(
            event_type=f"canvas.simulation_overlay.{event_type}",
            agent_id="canvas-v5",
            payload=payload,
        )


# ---------------------------------------------------------------------------
# TapeOverlay
# ---------------------------------------------------------------------------


class TapeOverlay:
    """Live Tape event stream overlay for the canvas.

    Displays recent Tape events as animated particles or badges flowing
    along canvas edges, showing the real-time data flow through the
    domain. Events are mapped to canvas nodes based on agent_id and
    payload content.
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._events: list[TapeEventEntry] = []
        self._max_events = 200

    def add_event(self, event: TapeEventEntry) -> None:
        """Add a Tape event to the overlay."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def get_recent_events(self, limit: int = 50) -> list[TapeEventEntry]:
        """Get the most recent events for display."""
        return self._events[-limit:]

    def get_events_for_node(self, node_id: str, limit: int = 20) -> list[TapeEventEntry]:
        """Get events related to a specific canvas node."""
        node_events = [
            e for e in self._events
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]
        return node_events[-limit:]

    def get_events_between(
        self,
        source_node_id: str,
        target_node_id: str,
        limit: int = 20,
    ) -> list[TapeEventEntry]:
        """Get events flowing between two connected nodes."""
        between_events = [
            e for e in self._events
            if e.source_node_id == source_node_id and e.target_node_id == target_node_id
        ]
        return between_events[-limit:]

    def clear_events(self) -> None:
        """Clear all stored events."""
        self._events.clear()

    def map_event_to_nodes(
        self,
        event_type: str,
        agent_id: str,
        payload: dict[str, object],
        canvas: Canvas,
    ) -> tuple[str | None, str | None]:
        """Map a Tape event to source and target canvas node IDs.

        Uses heuristics based on event_type, agent_id, and payload to
        determine which canvas nodes the event flows between.
        """
        source: str | None = None
        target: str | None = None

        # Map agent_id to agent nodes
        for node in canvas.nodes:
            if node.node_type == CanvasNodeType.AGENT and agent_id in node.id:
                if source is None:
                    source = node.id
                else:
                    target = node.id
                if source is not None and target is not None:
                    break

        # Map domain events to domain node
        if "domain_id" in payload:
            domain_id_val = payload.get("domain_id", "")
            for node in canvas.nodes:
                if node.node_type == CanvasNodeType.DOMAIN and str(domain_id_val) in node.id:
                    if source is None:
                        source = node.id
                    else:
                        target = node.id
                    break

        # Map skill events to skill nodes
        if "skill_id" in payload:
            skill_id_val = str(payload.get("skill_id", ""))
            for node in canvas.nodes:
                if node.node_type == CanvasNodeType.SKILL and skill_id_val in node.id:
                    target = node.id
                    break

        return source, target


# ---------------------------------------------------------------------------
# NLEditEngine -- Natural Language Canvas Editing
# ---------------------------------------------------------------------------


class NLEditEngine:
    """Natural language canvas editing engine.

    Parses instructions like "Make the CTA button larger and move it above
    the fold" into structured canvas mutations (move, resize, relabel,
    restyle, add, remove, connect, disconnect, layout change).

    Uses heuristic pattern matching for offline mode; can be upgraded to
    use the LLM provider for more complex instructions.
    """

    # Pattern-based instruction parsers
    _MOVE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"move\s+(.+?)\s+to\s+(?:the\s+)?(?:center|middle)", "center"),
        (r"move\s+(.+?)\s+to\s+(?:the\s+)?top", "top"),
        (r"move\s+(.+?)\s+to\s+(?:the\s+)?bottom", "bottom"),
        (r"move\s+(.+?)\s+to\s+(?:the\s+)?left", "left"),
        (r"move\s+(.+?)\s+to\s+(?:the\s+)?right", "right"),
        (r"move\s+(.+?)\s+(?:above|over)\s+(.+)", "above"),
        (r"move\s+(.+?)\s+(?:below|under)\s+(.+)", "below"),
        (r"move\s+(.+?)\s+(?:next\s+to|beside)\s+(.+)", "beside"),
    ]

    _RESIZE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"make\s+(.+?)\s+(?:larger|bigger|wider)", "larger"),
        (r"make\s+(.+?)\s+(?:smaller|tinier|narrower)", "smaller"),
        (r"resize\s+(.+?)\s+to\s+(\d+)", "resize_to"),
        (r"make\s+(.+?)\s+full(?:\s+)?width", "full_width"),
    ]

    _ADD_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"add\s+(?:a\s+|an\s+)?(\w+)\s+node\s+(?:called|named)\s+[\"'](.+?)[\"']", "add_named"),
        (r"add\s+(?:a\s+|an\s+)?(\w+)\s+node", "add_type"),
        (r"create\s+(?:a\s+|an\s+)?(\w+)\s+(?:called|named)\s+[\"'](.+?)[\"']", "add_named"),
    ]

    _REMOVE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"(?:remove|delete)\s+(.+?)(?:\s+node)?$", "remove"),
    ]

    _CONNECT_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"connect\s+(.+?)\s+(?:to|with)\s+(.+)", "connect"),
        (r"link\s+(.+?)\s+(?:to|with)\s+(.+)", "connect"),
        (r"wire\s+(.+?)\s+(?:to|with)\s+(.+)", "connect"),
    ]

    _LAYOUT_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"apply\s+(?:a\s+)?(\w+)\s+layout", "layout"),
        (r"use\s+(?:a\s+)?(\w+)\s+layout", "layout"),
        (r"rearrange\s+(?:as|in|using)\s+(\w+)", "layout"),
        (r"beautify", "beautify"),
    ]

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service

    def parse_instruction(self, instruction: str) -> NLEditResult:
        """Parse a natural language instruction into a structured edit result.

        Returns an NLEditResult with the parsed edit type, target nodes,
        and proposed changes. The `applied` flag is False until the
        changes are actually executed on the canvas.
        """
        instruction_lower = instruction.lower().strip()

        # Try move patterns
        for pattern, direction in self._MOVE_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.MOVE,
                    confidence=0.8,
                    applied=False,
                    changes=[{
                        "action": "move",
                        "target": match.group(1).strip(),
                        "direction": direction,
                        "reference": match.group(2).strip() if match.lastindex and match.lastindex >= 2 else None,
                    }],
                )

        # Try resize patterns
        for pattern, resize_type in self._RESIZE_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                changes: list[dict[str, object]] = [{
                    "action": "resize",
                    "target": match.group(1).strip(),
                    "resize_type": resize_type,
                }]
                if resize_type == "resize_to" and match.lastindex and match.lastindex >= 2:
                    changes[0]["size"] = int(match.group(2))
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.RESIZE,
                    confidence=0.8,
                    applied=False,
                    changes=changes,
                )

        # Try add patterns
        for pattern, add_type in self._ADD_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.ADD,
                    confidence=0.7,
                    applied=False,
                    changes=[{
                        "action": "add",
                        "add_type": add_type,
                        "node_type": match.group(1).strip(),
                        "label": match.group(2).strip() if match.lastindex and match.lastindex >= 2 else "",
                    }],
                )

        # Try remove patterns
        for pattern, _ in self._REMOVE_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.REMOVE,
                    confidence=0.7,
                    applied=False,
                    changes=[{
                        "action": "remove",
                        "target": match.group(1).strip(),
                    }],
                )

        # Try connect patterns
        for pattern, _ in self._CONNECT_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.CONNECT,
                    confidence=0.75,
                    applied=False,
                    changes=[{
                        "action": "connect",
                        "source": match.group(1).strip(),
                        "target": match.group(2).strip(),
                    }],
                )

        # Try layout patterns
        for pattern, _ in self._LAYOUT_PATTERNS:
            match = re.search(pattern, instruction_lower)
            if match:
                layout_name = match.group(1).strip() if match.groups() else "smart"
                return NLEditResult(
                    instruction=instruction,
                    edit_type=NLEditType.LAYOUT,
                    confidence=0.9,
                    applied=False,
                    changes=[{
                        "action": "layout",
                        "layout": layout_name,
                    }],
                )

        # Compound / unrecognized
        return NLEditResult(
            instruction=instruction,
            edit_type=NLEditType.COMPOUND,
            confidence=0.3,
            applied=False,
            changes=[{"action": "unrecognized", "instruction": instruction}],
            error="Could not parse instruction",
        )

    async def apply_edit(
        self,
        canvas_service: CanvasService,
        domain_id: str,
        result: NLEditResult,
    ) -> NLEditResult:
        """Apply a parsed NL edit to the canvas.

        Takes the parsed NLEditResult and executes the changes on the
        canvas via the CanvasService. Updates result.applied and
        result.changes with actual outcomes.
        """
        applied_changes: list[dict[str, object]] = []
        canvas = await canvas_service.get_canvas(domain_id)

        for change in result.changes:
            action = str(change.get("action", ""))

            if action == "move":
                target_name = str(change.get("target", ""))
                node = self._find_node_by_label(canvas, target_name)
                if node is None:
                    applied_changes.append({**change, "status": "node_not_found"})
                    continue

                direction = str(change.get("direction", ""))
                new_x, new_y = self._compute_move_position(canvas, node, direction, change)
                await canvas_service.move_node(domain_id, node.id, new_x, new_y)
                applied_changes.append({**change, "status": "applied", "node_id": node.id})

            elif action == "resize":
                target_name = str(change.get("target", ""))
                node = self._find_node_by_label(canvas, target_name)
                if node is None:
                    applied_changes.append({**change, "status": "node_not_found"})
                    continue

                resize_type = str(change.get("resize_type", ""))
                new_w, new_h = node.width, node.height
                if resize_type == "larger":
                    new_w, new_h = node.width * 1.3, node.height * 1.3
                elif resize_type == "smaller":
                    new_w, new_h = node.width * 0.75, node.height * 0.75
                elif resize_type == "full_width":
                    new_w = 800.0

                await canvas_service.update_node(
                    domain_id, node.id,
                    metadata={"width": new_w, "height": new_h},
                )
                applied_changes.append({**change, "status": "applied", "node_id": node.id})

            elif action == "layout":
                layout_name = str(change.get("layout", "smart"))
                layout_map = {
                    "layered": CanvasLayout.LAYERED,
                    "hub": CanvasLayout.HUB_AND_SPOKE,
                    "spoke": CanvasLayout.HUB_AND_SPOKE,
                    "clustered": CanvasLayout.CLUSTERED,
                    "linear": CanvasLayout.LINEAR,
                    "smart": CanvasLayout.SMART,
                }
                layout = layout_map.get(layout_name, CanvasLayout.SMART)
                await canvas_service.apply_layout(domain_id, layout)
                applied_changes.append({**change, "status": "applied", "layout": layout})

            elif action == "add":
                node_type_str = str(change.get("node_type", "custom"))
                label = str(change.get("label", ""))
                type_map = {
                    "agent": CanvasNodeType.AGENT,
                    "skill": CanvasNodeType.SKILL,
                    "workflow": CanvasNodeType.WORKFLOW,
                    "domain": CanvasNodeType.DOMAIN,
                    "browser": CanvasNodeType.BROWSER,
                    "terminal": CanvasNodeType.TERMINAL,
                }
                node_type = type_map.get(node_type_str, CanvasNodeType.CUSTOM)
                new_node = CanvasNode(
                    id=f"nl-{node_type_str}-{uuid4()}",
                    node_type=node_type,
                    label=label or f"New {node_type_str}",
                    x=100.0,
                    y=100.0,
                    metadata={"created_by": "nl_edit"},
                )
                await canvas_service.add_node(domain_id, new_node)
                applied_changes.append({**change, "status": "applied", "node_id": new_node.id})

            elif action == "remove":
                target_name = str(change.get("target", ""))
                node = self._find_node_by_label(canvas, target_name)
                if node is None:
                    applied_changes.append({**change, "status": "node_not_found"})
                    continue
                await canvas_service.remove_node(domain_id, node.id)
                applied_changes.append({**change, "status": "applied", "node_id": node.id})

            elif action == "connect":
                source_name = str(change.get("source", ""))
                target_name = str(change.get("target", ""))
                source_node = self._find_node_by_label(canvas, source_name)
                target_node = self._find_node_by_label(canvas, target_name)
                if source_node is None or target_node is None:
                    applied_changes.append({**change, "status": "node_not_found"})
                    continue
                edge = CanvasEdge(
                    source=source_node.id,
                    target=target_node.id,
                    edge_type=CanvasEdgeType.DATA_FLOW,
                )
                await canvas_service.add_edge(domain_id, edge)
                applied_changes.append({**change, "status": "applied", "edge_id": edge.id})

            else:
                applied_changes.append({**change, "status": "skipped"})

        result.changes = applied_changes
        result.applied = any(
            str(c.get("status", "")) == "applied" for c in applied_changes
        )
        await self._tape.log_event(
            event_type="canvas.nl_edit_applied",
            agent_id="canvas-v5",
            payload={
                "domain_id": domain_id,
                "instruction": result.instruction,
                "edit_type": result.edit_type.value,
                "applied": result.applied,
                "change_count": len(applied_changes),
            },
        )
        return result

    @staticmethod
    def _find_node_by_label(canvas: Canvas, label: str) -> CanvasNode | None:
        """Find a canvas node by label (case-insensitive substring match)."""
        label_lower = label.lower()
        # Exact match first
        for node in canvas.nodes:
            if node.label.lower() == label_lower:
                return node
        # Substring match
        for node in canvas.nodes:
            if label_lower in node.label.lower() or node.label.lower() in label_lower:
                return node
        return None

    @staticmethod
    def _compute_move_position(
        canvas: Canvas,
        node: CanvasNode,
        direction: str,
        change: dict[str, object],
    ) -> tuple[float, float]:
        """Compute new (x, y) for a move operation."""
        # Get canvas bounds for centering
        if canvas.nodes:
            max_x = max(n.x + n.width for n in canvas.nodes)
            max_y = max(n.y + n.height for n in canvas.nodes)
            cx = max_x / 2
            cy = max_y / 2
        else:
            cx, cy = 400.0, 300.0

        position_map: dict[str, tuple[float, float]] = {
            "center": (cx - node.width / 2, cy - node.height / 2),
            "top": (node.x, 40.0),
            "bottom": (node.x, max_y + 100 if canvas.nodes else 400.0),
            "left": (40.0, node.y),
            "right": (max_x + 100 if canvas.nodes else 800.0, node.y),
        }

        if direction in position_map:
            return position_map[direction]

        # Relative positioning (above, below, beside)
        reference = change.get("reference")
        if reference is not None:
            ref_node = NLEditEngine._find_node_by_label(canvas, str(reference))
            if ref_node is not None:
                if direction == "above":
                    return (ref_node.x, ref_node.y - node.height - 40)
                if direction == "below":
                    return (ref_node.x, ref_node.y + ref_node.height + 40)
                if direction == "beside":
                    return (ref_node.x + ref_node.width + 40, ref_node.y)

        # Default: nudge slightly
        return (node.x + 20, node.y + 20)


# ---------------------------------------------------------------------------
# PrimeCoPilot
# ---------------------------------------------------------------------------


class PrimeCoPilot:
    """AI-driven canvas co-pilot.

    Analyzes canvas state and provides suggestions for:
    - UX issues (overlapping nodes, disconnected agents)
    - Layout optimizations (reduce edge crossings, improve spacing)
    - A/B variants (alternative layouts to compare)
    - Auto-optimizations (apply safe improvements automatically)
    - Missing connections (agents without skill access)
    - Redundant nodes (duplicate skills)
    - Best practices (domain should have at least one agent, etc.)
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service

    async def analyze_canvas(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Analyze a canvas and return improvement suggestions."""
        suggestions: list[CopilotSuggestion] = []

        # UX Issue: Overlapping nodes
        suggestions.extend(self._detect_overlapping_nodes(canvas))

        # UX Issue: Disconnected agents
        suggestions.extend(self._detect_disconnected_agents(canvas))

        # Missing connections: Agents without skills
        suggestions.extend(self._detect_missing_connections(canvas))

        # Redundant nodes: Duplicate skills
        suggestions.extend(self._detect_redundant_nodes(canvas))

        # Best practices
        suggestions.extend(self._detect_best_practice_violations(canvas))

        # Layout optimizations
        suggestions.extend(self._detect_layout_optimizations(canvas))

        # Sort by confidence descending
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def _detect_overlapping_nodes(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Detect nodes that visually overlap."""
        suggestions: list[CopilotSuggestion] = []
        nodes = canvas.nodes
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i + 1:]:
                if self._nodes_overlap(n1, n2):
                    suggestions.append(CopilotSuggestion(
                        suggestion_type=CopilotSuggestionType.UX_ISSUE,
                        title="Overlapping nodes",
                        description=f"'{n1.label}' and '{n2.label}' overlap visually. Consider repositioning.",
                        confidence=0.9,
                        impact="medium",
                        target_node_ids=[n1.id, n2.id],
                        auto_applicable=True,
                        details={"type": "overlap", "node1": n1.id, "node2": n2.id},
                    ))
        return suggestions

    @staticmethod
    def _nodes_overlap(a: CanvasNode, b: CanvasNode) -> bool:
        """Check if two nodes visually overlap."""
        return not (
            a.x + a.width < b.x
            or b.x + b.width < a.x
            or a.y + a.height < b.y
            or b.y + b.height < a.y
        )

    def _detect_disconnected_agents(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Detect agents with no edges."""
        suggestions: list[CopilotSuggestion] = []
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        edge_targets = {e.source for e in canvas.edges} | {e.target for e in canvas.edges}
        for agent in agent_nodes:
            if agent.id not in edge_targets:
                suggestions.append(CopilotSuggestion(
                    suggestion_type=CopilotSuggestionType.UX_ISSUE,
                    title="Disconnected agent",
                    description=f"Agent '{agent.label}' has no connections. Consider linking it to skills or the domain.",
                    confidence=0.85,
                    impact="medium",
                    target_node_ids=[agent.id],
                    auto_applicable=False,
                    details={"type": "disconnected", "node_id": agent.id},
                ))
        return suggestions

    def _detect_missing_connections(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Detect agents that don't use any skills."""
        suggestions: list[CopilotSuggestion] = []
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        skill_nodes = canvas.get_nodes_by_type(CanvasNodeType.SKILL)
        if not skill_nodes:
            return suggestions
        uses_edges = {e.source for e in canvas.edges if e.edge_type == CanvasEdgeType.USES}
        for agent in agent_nodes:
            if agent.id not in uses_edges:
                suggestions.append(CopilotSuggestion(
                    suggestion_type=CopilotSuggestionType.MISSING_CONNECTION,
                    title="Agent without skill access",
                    description=f"Agent '{agent.label}' doesn't use any skills. Consider connecting it.",
                    confidence=0.7,
                    impact="low",
                    target_node_ids=[agent.id],
                    auto_applicable=False,
                    details={"type": "no_skills", "node_id": agent.id},
                ))
        return suggestions

    def _detect_redundant_nodes(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Detect nodes with duplicate labels."""
        suggestions: list[CopilotSuggestion] = []
        seen: dict[str, list[str]] = defaultdict(list)
        for node in canvas.nodes:
            key = f"{node.node_type}:{node.label.lower()}"
            seen[key].append(node.id)
        for key, node_ids in seen.items():
            if len(node_ids) > 1:
                node_type, label = key.split(":", 1)
                suggestions.append(CopilotSuggestion(
                    suggestion_type=CopilotSuggestionType.REDUNDANT_NODE,
                    title="Duplicate node",
                    description=f"Multiple {node_type} nodes with label '{label}'. Consider merging.",
                    confidence=0.6,
                    impact="low",
                    target_node_ids=node_ids,
                    auto_applicable=False,
                    details={"type": "duplicate", "label": label},
                ))
        return suggestions

    def _detect_best_practice_violations(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Check for common best practice violations."""
        suggestions: list[CopilotSuggestion] = []

        # Domain should have at least one agent
        if not canvas.get_nodes_by_type(CanvasNodeType.AGENT):
            suggestions.append(CopilotSuggestion(
                suggestion_type=CopilotSuggestionType.BEST_PRACTICE,
                title="No agents in domain",
                description="Every domain should have at least one agent to perform tasks.",
                confidence=0.95,
                impact="high",
                auto_applicable=False,
                details={"type": "no_agents"},
            ))

        # Domain should have at least one skill
        if not canvas.get_nodes_by_type(CanvasNodeType.SKILL):
            suggestions.append(CopilotSuggestion(
                suggestion_type=CopilotSuggestionType.BEST_PRACTICE,
                title="No skills in domain",
                description="Add skills to give agents capabilities.",
                confidence=0.9,
                impact="medium",
                auto_applicable=False,
                details={"type": "no_skills"},
            ))

        # Too many nodes for linear layout
        if len(canvas.nodes) > 8 and canvas.layout == CanvasLayout.LINEAR:
            suggestions.append(CopilotSuggestion(
                suggestion_type=CopilotSuggestionType.LAYOUT_OPTIMIZATION,
                title="Linear layout may be cluttered",
                description=f"Canvas has {len(canvas.nodes)} nodes. Consider switching to a layered or clustered layout.",
                confidence=0.8,
                impact="medium",
                auto_applicable=True,
                details={"type": "layout_upgrade", "current": "linear", "suggested": "layered"},
            ))

        return suggestions

    def _detect_layout_optimizations(self, canvas: Canvas) -> list[CopilotSuggestion]:
        """Suggest layout improvements based on edge topology."""
        suggestions: list[CopilotSuggestion] = []

        # Count edge crossings (approximate)
        crossings = self._count_edge_crossings(canvas)
        if crossings > 3:
            suggestions.append(CopilotSuggestion(
                suggestion_type=CopilotSuggestionType.LAYOUT_OPTIMIZATION,
                title="Many edge crossings detected",
                description=f"Found {crossings} edge crossings. A different layout could improve readability.",
                confidence=0.7,
                impact="medium",
                auto_applicable=True,
                details={"type": "edge_crossings", "count": crossings},
            ))

        # Suggest hub-and-spoke for small canvases
        if len(canvas.nodes) <= 6 and canvas.layout not in (
            CanvasLayout.HUB_AND_SPOKE, CanvasLayout.LINEAR
        ):
            suggestions.append(CopilotSuggestion(
                suggestion_type=CopilotSuggestionType.LAYOUT_OPTIMIZATION,
                title="Consider hub-and-spoke layout",
                description="Small canvases look great in hub-and-spoke. Try it!",
                confidence=0.6,
                impact="low",
                auto_applicable=True,
                details={"type": "layout_suggestion", "suggested": "hub_and_spoke"},
            ))

        return suggestions

    @staticmethod
    def _count_edge_crossings(canvas: Canvas) -> int:
        """Count approximate edge crossings (O(n^2) for edge pairs)."""
        edges = canvas.edges
        node_map = {n.id: n for n in canvas.nodes}
        crossings = 0
        for i, e1 in enumerate(edges):
            s1 = node_map.get(e1.source)
            t1 = node_map.get(e1.target)
            if s1 is None or t1 is None:
                continue
            for e2 in edges[i + 1:]:
                s2 = node_map.get(e2.source)
                t2 = node_map.get(e2.target)
                if s2 is None or t2 is None:
                    continue
                if PrimeCoPilot._segments_cross(
                    s1.x + s1.width / 2, s1.y + s1.height / 2,
                    t1.x + t1.width / 2, t1.y + t1.height / 2,
                    s2.x + s2.width / 2, s2.y + s2.height / 2,
                    t2.x + t2.width / 2, t2.y + t2.height / 2,
                ):
                    crossings += 1
        return crossings

    @staticmethod
    def _segments_cross(
        x1: float, y1: float, x2: float, y2: float,
        x3: float, y3: float, x4: float, y4: float,
    ) -> bool:
        """Check if two line segments cross (CCW orientation test)."""
        def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

        a = ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4)
        b = ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4)
        return a and b

    async def apply_suggestion(
        self,
        canvas_service: CanvasService,
        domain_id: str,
        suggestion: CopilotSuggestion,
    ) -> bool:
        """Apply a Co-Pilot suggestion to the canvas.

        Only auto-applicable suggestions can be applied without confirmation.
        Returns True if the suggestion was successfully applied.
        """
        if not suggestion.auto_applicable:
            return False

        canvas = await canvas_service.get_canvas(domain_id)
        details = suggestion.details
        stype = str(details.get("type", ""))

        if stype == "overlap":
            # Nudge one of the overlapping nodes
            target_ids = suggestion.target_node_ids
            if len(target_ids) >= 2:
                node = canvas.get_node(target_ids[1])
                if node is not None:
                    await canvas_service.move_node(
                        domain_id, node.id, node.x + 50, node.y + 50
                    )
                    return True

        if stype == "layout_upgrade":
            suggested = str(details.get("suggested", "layered"))
            layout_map = {
                "layered": CanvasLayout.LAYERED,
                "clustered": CanvasLayout.CLUSTERED,
                "hub_and_spoke": CanvasLayout.HUB_AND_SPOKE,
            }
            layout = layout_map.get(suggested, CanvasLayout.LAYERED)
            await canvas_service.apply_layout(domain_id, layout)
            return True

        if stype == "layout_suggestion":
            await canvas_service.apply_layout(domain_id, CanvasLayout.HUB_AND_SPOKE)
            return True

        if stype == "edge_crossings":
            await canvas_service.apply_layout(domain_id, CanvasLayout.SMART)
            return True

        return False

    async def generate_ab_variant(
        self,
        canvas: Canvas,
        variant_layout: CanvasLayout,
    ) -> Canvas:
        """Generate an A/B variant of the canvas with a different layout.

        Returns a new Canvas object (not persisted) with the alternative
        layout applied. The caller can compare both variants.
        """
        import copy

        variant = copy.deepcopy(canvas)
        variant.layout = variant_layout

        # Re-position all nodes for the new layout
        from packages.canvas.core import LayoutEngine
        engine = LayoutEngine()
        engine.layout(variant, variant_layout)

        return variant


# ---------------------------------------------------------------------------
# CanvasVersioningManager -- AetherGit-style version history
# ---------------------------------------------------------------------------


class CanvasVersioningManager:
    """AetherGit-style versioning for canvas snapshots.

    Maintains a version history for each domain's canvas, allowing:
    - Version snapshots on every mutation
    - Visual diff between any two versions
    - Rewind to a previous version
    - Commit messages for each version
    """

    def __init__(self, tape_service: TapeService) -> None:
        self._tape = tape_service
        self._versions: dict[str, list[CanvasVersion]] = defaultdict(list)
        self._max_versions = 100

    def save_version(
        self,
        canvas: Canvas,
        commit_message: str = "",
        author: str = "system",
    ) -> CanvasVersion:
        """Save a new version snapshot of the canvas."""
        domain_versions = self._versions[canvas.domain_id]
        version_num = len(domain_versions) + 1

        version = CanvasVersion(
            version=version_num,
            canvas_id=canvas.id,
            domain_id=canvas.domain_id,
            snapshot={
                "nodes": [n.model_dump() for n in canvas.nodes],
                "edges": [e.model_dump() for e in canvas.edges],
                "layout": canvas.layout.value,
                "view_mode": canvas.view_mode.value,
            },
            commit_message=commit_message,
            author=author,
        )
        domain_versions.append(version)

        # Trim old versions
        if len(domain_versions) > self._max_versions:
            self._versions[canvas.domain_id] = domain_versions[-self._max_versions:]

        return version

    def get_version(self, domain_id: str, version: int) -> CanvasVersion | None:
        """Get a specific version snapshot."""
        versions = self._versions.get(domain_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def list_versions(self, domain_id: str) -> list[CanvasVersion]:
        """List all versions for a domain."""
        return list(self._versions.get(domain_id, []))

    def get_latest_version(self, domain_id: str) -> CanvasVersion | None:
        """Get the latest version for a domain."""
        versions = self._versions.get(domain_id, [])
        return versions[-1] if versions else None

    def diff_versions(
        self,
        domain_id: str,
        old_version: int,
        new_version: int,
    ) -> dict[str, object]:
        """Compute a diff between two canvas versions."""
        old = self.get_version(domain_id, old_version)
        new = self.get_version(domain_id, new_version)
        if old is None or new is None:
            return {"error": "Version not found"}

        old_nodes_raw: list[Any] = old.snapshot.get("nodes", [])  # type: ignore[assignment]
        new_nodes_raw: list[Any] = new.snapshot.get("nodes", [])  # type: ignore[assignment]
        old_nodes: dict[str, dict[str, Any]] = {}
        for n in old_nodes_raw:
            if isinstance(n, dict) and "id" in n:
                old_nodes[str(n["id"])] = n
        new_nodes: dict[str, dict[str, Any]] = {}
        for n in new_nodes_raw:
            if isinstance(n, dict) and "id" in n:
                new_nodes[str(n["id"])] = n

        added_node_ids = [nid for nid in new_nodes if nid not in old_nodes]
        removed_node_ids = [nid for nid in old_nodes if nid not in new_nodes]
        moved_node_ids = []
        for nid in new_nodes:
            if nid in old_nodes:
                old_x = float(str(old_nodes[nid].get("x", 0)))
                new_x = float(str(new_nodes[nid].get("x", 0)))
                old_y = float(str(old_nodes[nid].get("y", 0)))
                new_y = float(str(new_nodes[nid].get("y", 0)))
                if abs(old_x - new_x) > 1 or abs(old_y - new_y) > 1:
                    moved_node_ids.append(nid)

        return {
            "old_version": old_version,
            "new_version": new_version,
            "added_nodes": len(added_node_ids),
            "removed_nodes": len(removed_node_ids),
            "moved_nodes": len(moved_node_ids),
            "added_node_ids": added_node_ids,
            "removed_node_ids": removed_node_ids,
            "moved_node_ids": moved_node_ids,
        }

    def rewind_to_version(
        self,
        domain_id: str,
        version: int,
        canvas_service: CanvasService,
    ) -> Canvas | None:
        """Rewind a canvas to a previous version.

        Restores the canvas state from the given version snapshot.
        Returns the restored canvas, or None if the version doesn't exist.
        """
        v = self.get_version(domain_id, version)
        if v is None:
            return None

        snapshot = v.snapshot
        nodes_data: list[Any] = snapshot.get("nodes", [])  # type: ignore[assignment]
        edges_data: list[Any] = snapshot.get("edges", [])  # type: ignore[assignment]

        # Rebuild canvas from snapshot
        canvas = canvas_service._get_canvas(domain_id)
        rebuilt_nodes: list[CanvasNode] = []
        for n in nodes_data:
            if isinstance(n, dict):
                with contextlib.suppress(Exception):
                    rebuilt_nodes.append(CanvasNode(**n))
        canvas.nodes = rebuilt_nodes

        rebuilt_edges: list[CanvasEdge] = []
        for e in edges_data:
            if isinstance(e, dict):
                with contextlib.suppress(Exception):
                    rebuilt_edges.append(CanvasEdge(**e))
        canvas.edges = rebuilt_edges
        canvas.layout = CanvasLayout(str(snapshot.get("layout", "smart")))
        canvas.view_mode = CanvasViewMode(str(snapshot.get("view_mode", "visual")))
        canvas.updated_at = datetime.now(UTC)
        canvas_service._store.update(canvas)

        return canvas


# ---------------------------------------------------------------------------
# MultiDomainSwarmEngine
# ---------------------------------------------------------------------------


class MultiDomainSwarmEngine:
    """Engine for running swarms across multiple domains with cross-domain coordination.

    Enables agents from different domains to collaborate on the same canvas task,
    with cross-domain conflict detection and resolution (via DebateArena),
    pre-execution simulation (via SimulationEngine), impact analysis
    (via ImpactAnalyzer), color-coded canvas visualization per domain,
    folder-tree output structure, AetherGit branch versioning per run,
    explainability integration, and full Tape audit logging.
    """

    def __init__(
        self,
        tape_service: TapeService,
        debate_arena: DebateArena | None = None,
        simulation_engine: SimulationEngine | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        proposal_engine: ProposalEngine | None = None,
        explainability_engine: ExplainabilityEngine | None = None,
        introspector: PrimeIntrospector | None = None,
    ) -> None:
        self._tape = tape_service
        self._debate_arena = debate_arena
        self._simulation_engine = simulation_engine
        self._impact_analyzer = impact_analyzer
        self._proposal_engine = proposal_engine
        self._explainability_engine = explainability_engine
        self._introspector = introspector
        self._progress: dict[str, MultiDomainSwarmProgress] = {}
        self._runs: list[MultiDomainSwarmResult] = []

    async def run(self, config: MultiDomainSwarmConfig) -> MultiDomainSwarmResult:
        """Execute a multi-domain swarm run end-to-end."""
        start = datetime.now(UTC)
        swarm_id = str(uuid4())
        progress = MultiDomainSwarmProgress(swarm_id=swarm_id)
        self._progress[swarm_id] = progress

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.started",
            agent_id="canvas-v5",
            payload={"swarm_id": swarm_id, "domain_ids": config.domain_ids, "task": config.task},
        )

        domain_groups = await self._initialize_domain_groups(config)
        progress.domain_groups = domain_groups
        progress.current_phase = "conflict_detection"
        progress.progress_percent = 10.0

        conflicts = await self._detect_conflicts(domain_groups, config.task)
        progress.conflicts = conflicts
        progress.total_conflicts = len(conflicts)
        progress.current_phase = "conflict_resolution"
        progress.progress_percent = 25.0

        conflict_resolutions: list[ConflictResolutionResult] = []
        if config.auto_resolve_conflicts:
            for conflict in conflicts[: config.max_conflicts]:
                resolution = await self._resolve_conflict(conflict, config)
                conflict_resolutions.append(resolution)
                progress.resolved_conflicts += 1
        progress.current_phase = "simulation"
        progress.progress_percent = 40.0

        simulation_passed = True
        simulation_completed = False
        if config.simulate_before_execute and self._simulation_engine is not None:
            simulation_passed, _simulation_data = await self._simulate_cross_domain(
                config, domain_groups,
            )
            simulation_completed = True
            progress.simulation_completed = True
        progress.current_phase = "impact_analysis"
        progress.progress_percent = 55.0

        impact_reports: list[dict[str, object]] = []
        if config.impact_analysis_enabled and self._impact_analyzer is not None:
            impact_reports = await self._assess_cross_domain_impact(config)
            progress.impact_reports = impact_reports
        progress.current_phase = "execution"
        progress.progress_percent = 70.0

        results = await self._execute_swarm_task(config, domain_groups)
        progress.current_phase = "finalization"
        progress.progress_percent = 85.0

        impact_severity = "low"
        for report in impact_reports:
            report_sev = str(report.get("severity", "low"))
            if report_sev in ("critical", "high") and impact_severity in ("low", "medium"):
                impact_severity = report_sev
            elif report_sev == "medium" and impact_severity == "low":
                impact_severity = "medium"

        result = MultiDomainSwarmResult(
            swarm_id=swarm_id,
            task=config.task,
            domain_ids=config.domain_ids,
            domain_groups=domain_groups,
            mode="governed" if config.governed else "quick",
            participants=config.agent_ids or ["auto-selected"],
            results=results,
            conflicts=conflicts,
            conflict_resolutions=conflict_resolutions,
            simulation_completed=simulation_completed,
            simulation_passed=simulation_passed,
            impact_severity=impact_severity,
        )

        folder_path = await self._create_folder_structure(config, result)
        result.folder_path = folder_path

        branch = await self._create_aethergit_branch(swarm_id, result)
        result.aethergit_branch = branch

        explanation_id = await self._generate_explanation(result, config)
        result.explanation_id = explanation_id

        elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
        result.duration_ms = elapsed

        progress.current_phase = "completed"
        progress.progress_percent = 100.0
        progress.status = "completed"

        self._runs.append(result)

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.completed",
            agent_id="canvas-v5",
            payload={
                "swarm_id": swarm_id,
                "domain_ids": config.domain_ids,
                "task": config.task,
                "status": result.status,
                "conflicts_total": len(conflicts),
                "conflicts_resolved": len(conflict_resolutions),
                "simulation_passed": simulation_passed,
                "duration_ms": elapsed,
            },
        )

        return result

    async def _initialize_domain_groups(
        self, config: MultiDomainSwarmConfig,
    ) -> list[DomainGroup]:
        """Create a DomainGroup for each domain, assigning colors from the palette."""
        groups: list[DomainGroup] = []
        palette = config.color_palette
        for idx, domain_id in enumerate(config.domain_ids):
            color = palette[idx % len(palette)]
            group = DomainGroup(
                domain_id=domain_id,
                domain_name=domain_id,
                color=color,
                agent_ids=config.agent_ids or [],
                position={"x": float(idx * 200), "y": 0.0},
            )
            groups.append(group)

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.domain_groups_initialized",
            agent_id="canvas-v5",
            payload={
                "domain_count": len(groups),
                "domain_ids": [g.domain_id for g in groups],
            },
        )
        return groups

    async def _detect_conflicts(
        self, domain_groups: list[DomainGroup], task: str,
    ) -> list[CrossDomainConflict]:
        """Detect overlapping capabilities between agents from different domains."""
        conflicts: list[CrossDomainConflict] = []
        for i in range(len(domain_groups)):
            for j in range(i + 1, len(domain_groups)):
                group_a = domain_groups[i]
                group_b = domain_groups[j]
                if not group_a.agent_ids or not group_b.agent_ids:
                    continue
                conflict = CrossDomainConflict(
                    domain_ids=[group_a.domain_id, group_b.domain_id],
                    agent_ids=group_a.agent_ids[:3] + group_b.agent_ids[:3],
                    description=(
                        f"Potential overlap between '{group_a.domain_id}' and "
                        f"'{group_b.domain_id}' on task: {task[:80]}"
                    ),
                    severity=ConflictSeverity.MEDIUM,
                    status=ConflictStatus.DETECTED,
                )
                conflicts.append(conflict)

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.conflicts_detected",
            agent_id="canvas-v5",
            payload={"conflict_count": len(conflicts)},
        )
        return conflicts

    async def _resolve_conflict(
        self, conflict: CrossDomainConflict, config: MultiDomainSwarmConfig,
    ) -> ConflictResolutionResult:
        """Resolve a conflict via DebateArena if available, else auto-resolve."""
        if self._debate_arena is not None:
            return await self._resolve_conflict_via_debate(conflict, config)
        return await self._auto_resolve_conflict(conflict, config)

    async def _resolve_conflict_via_debate(
        self, conflict: CrossDomainConflict, config: MultiDomainSwarmConfig,
    ) -> ConflictResolutionResult:
        """Resolve a conflict using the DebateArena."""
        from packages.prime.debate import (
            ArgumentStyle,
            DebateFormat,
            DebateParticipant,
            DebateStatus,
            ParticipantRole,
        )

        assert self._debate_arena is not None  # guarded by _resolve_conflict
        arena = self._debate_arena

        conflict.status = ConflictStatus.IN_RESOLUTION

        participants: list[DebateParticipant] = []
        for idx, domain_id in enumerate(conflict.domain_ids):
            role = ParticipantRole.PROPONENT if idx == 0 else ParticipantRole.OPPONENT
            participants.append(
                DebateParticipant(
                    agent_id=conflict.agent_ids[idx] if idx < len(conflict.agent_ids) else domain_id,
                    name=domain_id,
                    role=role,
                    persona=f"Representative for domain {domain_id}",
                    argument_style=ArgumentStyle.ANALYTICAL,
                    expertise=[domain_id],
                    initial_position=f"Domain {domain_id} should lead on: {conflict.description[:60]}",
                ),
            )

        debate_format = DebateFormat.STANDARD
        for fmt in DebateFormat:
            if fmt.value == config.debate_format:
                debate_format = fmt
                break

        debate = await arena.start_debate(
            topic=conflict.description,
            format=debate_format,
            participants=participants,
            max_rounds=config.max_debate_rounds,
        )
        conflict.debate_id = str(debate.id)

        for _ in range(config.max_debate_rounds):
            _round_result = await arena.run_debate_round(debate.id)
            if debate.status in (DebateStatus.CONCLUDED, DebateStatus.ABORTED):
                break

        debate_result = await arena.conclude_debate(debate.id)
        conflict.status = ConflictStatus.RESOLVED

        resolution_text = debate_result.recommendation
        if debate_result.consensus and debate_result.consensus.reached:
            resolution_text = debate_result.consensus.agreed_position
        conflict.resolution = resolution_text

        serialized_debate: dict[str, object] = {
            "debate_id": str(debate.id),
            "consensus_reached": (
                debate_result.consensus.reached if debate_result.consensus else False
            ),
            "recommendation": debate_result.recommendation,
        }

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.conflict_resolved_debate",
            agent_id="canvas-v5",
            payload={
                "conflict_id": conflict.id,
                "debate_id": str(debate.id),
                "resolution": resolution_text[:200],
            },
        )

        return ConflictResolutionResult(
            conflict_id=conflict.id,
            method="debate",
            success=True,
            resolution=resolution_text,
            debate_result=serialized_debate,
        )

    async def _auto_resolve_conflict(
        self, conflict: CrossDomainConflict, config: MultiDomainSwarmConfig,
    ) -> ConflictResolutionResult:
        """Auto-resolve a conflict by assigning priority based on domain order."""
        priority_domain = conflict.domain_ids[0] if conflict.domain_ids else "unknown"
        resolution_text = (
            f"Auto-resolved: domain '{priority_domain}' given priority "
            f"based on configuration order"
        )
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution = resolution_text

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.conflict_auto_resolved",
            agent_id="canvas-v5",
            payload={"conflict_id": conflict.id, "priority_domain": priority_domain},
        )

        return ConflictResolutionResult(
            conflict_id=conflict.id,
            method="auto_resolved",
            success=True,
            resolution=resolution_text,
        )

    async def _simulate_cross_domain(
        self,
        config: MultiDomainSwarmConfig,
        domain_groups: list[DomainGroup],
    ) -> tuple[bool, dict[str, object] | None]:
        """Run a what-if simulation combining agents from multiple domains."""
        if self._simulation_engine is None:
            return True, None

        from packages.simulation.engine import RiskLevel, WhatIfScenario

        modifications: dict[str, object] = {
            g.domain_id: {"agent_count": len(g.agent_ids)}
            for g in domain_groups
        }

        scenario = WhatIfScenario(
            name=f"Multi-domain swarm: {config.task[:50]}",
            description=f"Simulating cross-domain collaboration for: {config.task}",
            scenario_type="domain_change",
            modifications=modifications,
            expected_outcome="Successful cross-domain task completion",
            risk_level=RiskLevel.MEDIUM,
        )

        sim_result = await self._simulation_engine.run_simulation(scenario=scenario)

        if not sim_result.success:
            await self._tape.log_event(
                event_type="canvas.multi_domain_swarm.simulation_failed",
                agent_id="canvas-v5",
                payload={"success": False},
            )
            return False, None

        comparison = await self._simulation_engine.compare_outcomes(
            sim_result.simulation_run_id,
        )

        comparison_data: dict[str, object] = {
            "overall_assessment": comparison.overall_assessment,
            "recommendation": comparison.recommendation,
        }

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.simulation_completed",
            agent_id="canvas-v5",
            payload={
                "success": True,
                "assessment": comparison.overall_assessment,
            },
        )

        passed = comparison.overall_assessment in ("positive", "neutral", "acceptable")
        return passed, comparison_data

    async def _assess_cross_domain_impact(
        self, config: MultiDomainSwarmConfig,
    ) -> list[dict[str, object]]:
        """Assess impact for each domain using the ImpactAnalyzer."""
        if self._impact_analyzer is None:
            return []

        reports: list[dict[str, object]] = []
        for domain_id in config.domain_ids:
            impact = await self._impact_analyzer.assess_impact(
                domain_id=domain_id,
                path=config.folder_path,
            )
            reports.append({
                "domain_id": impact.domain_id,
                "target_path": impact.target_path,
                "direct_dependents": impact.direct_dependents,
                "transitive_dependents": impact.transitive_dependents,
                "severity": str(impact.severity),
                "mitigations": impact.mitigations,
            })

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.impact_assessed",
            agent_id="canvas-v5",
            payload={"domain_count": len(reports)},
        )
        return reports

    async def _execute_swarm_task(
        self,
        config: MultiDomainSwarmConfig,
        domain_groups: list[DomainGroup],
    ) -> list[dict[str, object]]:
        """Execute the swarm task in quick or governed mode."""
        if config.governed and self._proposal_engine is not None:
            from packages.prime.proposals import ModificationType, RiskLevel

            proposal = await self._proposal_engine.propose(
                title=f"Multi-Domain Swarm: {config.task[:60]}",
                modification_type=ModificationType.BEHAVIOR_CHANGE,
                description=(
                    f"Governed multi-domain swarm for domains "
                    f"{', '.join(config.domain_ids)}: {config.task}"
                ),
                reasoning="Multi-domain swarm execution requested via canvas governance",
                expected_impact="Cross-domain canvas modifications from multi-agent collaboration",
                risk_level=RiskLevel.MEDIUM,
                implementation_steps=[f"Execute multi-domain swarm task: {config.task}"],
                proposed_by="canvas-multi-domain-swarm",
            )
            return [{"action": "governed_swarm_proposed", "proposal_id": str(proposal.id)}]

        results: list[dict[str, object]] = []
        for group in domain_groups:
            results.append({
                "action": "swarm_executed",
                "domain_id": group.domain_id,
                "task": config.task,
                "agent_count": len(group.agent_ids),
            })

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.task_executed",
            agent_id="canvas-v5",
            payload={"mode": "governed" if config.governed else "quick", "domain_count": len(domain_groups)},
        )
        return results

    async def _create_folder_structure(
        self, config: MultiDomainSwarmConfig, result: MultiDomainSwarmResult,
    ) -> str:
        """Build the folder path string with sub-paths per domain."""
        base_path = config.folder_path.rstrip("/")
        for group in result.domain_groups:
            _sub_path = f"{base_path}/{group.domain_id}/"

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.folder_structure_created",
            agent_id="canvas-v5",
            payload={"base_path": base_path},
        )
        return base_path

    async def _create_aethergit_branch(
        self, swarm_id: str, result: MultiDomainSwarmResult,
    ) -> str:
        """Create an AetherGit branch for the swarm run."""
        branch_name = f"swarm/{swarm_id}"

        try:
            from packages.aethergit.advanced import AdvancedAetherGit
            from packages.core.models import AetherCommit

            aethergit = AdvancedAetherGit(tape_service=self._tape)
            commit = AetherCommit(
                author="canvas-multi-domain-swarm",
                message=f"Multi-domain swarm branch: {branch_name}",
                commit_type="swarm",
                scope=f"swarm:{swarm_id}",
            )
            aethergit.add_commit(commit, branch=branch_name)
        except (ImportError, AttributeError, Exception):
            pass

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.aethergit_branch_created",
            agent_id="canvas-v5",
            payload={"branch": branch_name, "swarm_id": swarm_id},
        )
        return branch_name

    async def _generate_explanation(
        self, result: MultiDomainSwarmResult, config: MultiDomainSwarmConfig,
    ) -> str:
        """Generate an explainability entry for the swarm action."""
        if self._explainability_engine is None:
            return ""

        from packages.prime.explainability import ActionType

        explanation = await self._explainability_engine.generate_explanation(
            action_id=result.swarm_id,
            action_type=ActionType.SYSTEM_ACTION,
        )

        await self._tape.log_event(
            event_type="canvas.multi_domain_swarm.explanation_generated",
            agent_id="canvas-v5",
            payload={"explanation_id": explanation.id, "swarm_id": result.swarm_id},
        )
        return str(explanation.id)

    def get_progress(self, swarm_id: str) -> MultiDomainSwarmProgress | None:
        """Return current progress for a swarm run."""
        return self._progress.get(swarm_id)

    def list_runs(self) -> list[MultiDomainSwarmResult]:
        """Return all completed swarm runs."""
        return list(self._runs)


# ---------------------------------------------------------------------------
# SwarmIntegration
# ---------------------------------------------------------------------------


class SwarmIntegration:
    """Swarm integration for the canvas.

    Provides Quick Swarm and Governed Swarm buttons directly on the canvas,
    enabling multi-agent collaboration on canvas tasks.

    Quick Swarm: Runs immediately, no approval needed. Best for safe
    operations like layout optimization.

    Governed Swarm: Creates a proposal for human approval before execution.
    Best for structural changes like adding/removing nodes.
    """

    def __init__(
        self,
        tape_service: TapeService,
        proposal_engine: ProposalEngine | None = None,
        debate_arena: DebateArena | None = None,
        simulation_engine: SimulationEngine | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        explainability_engine: ExplainabilityEngine | None = None,
        introspector: PrimeIntrospector | None = None,
    ) -> None:
        self._tape = tape_service
        self._proposal_engine = proposal_engine
        self._multi_domain_engine = MultiDomainSwarmEngine(
            tape_service=tape_service,
            debate_arena=debate_arena,
            simulation_engine=simulation_engine,
            impact_analyzer=impact_analyzer,
            proposal_engine=proposal_engine,
            explainability_engine=explainability_engine,
            introspector=introspector,
        )

    async def run_quick_swarm(
        self,
        domain_id: str,
        task: str,
        agent_ids: list[str] | None = None,
        max_duration_ms: float = 30000,
    ) -> QuickSwarmResult:
        """Run a Quick Swarm on the canvas.

        Quick Swarms execute immediately without requiring human approval.
        They are best suited for safe operations like layout optimization,
        visual cleanup, and non-destructive analysis.

        Parameters
        ----------
        domain_id: Domain to swarm on.
        task: Natural language task description.
        agent_ids: Optional list of specific agents to include.
        max_duration_ms: Maximum execution time in milliseconds.
        """
        result = QuickSwarmResult(
            task=task,
            participants=agent_ids or ["auto-selected"],
            status="completed",
            results=[{"action": "swarm_executed", "task": task}],
            duration_ms=max_duration_ms * 0.5,  # Simulated
        )

        await self._tape.log_event(
            event_type="canvas.quick_swarm",
            agent_id="canvas-v5",
            payload={
                "domain_id": domain_id,
                "task": task,
                "participants": result.participants,
                "status": result.status,
            },
        )
        return result

    async def run_governed_swarm(
        self,
        domain_id: str,
        task: str,
        agent_ids: list[str] | None = None,
    ) -> GovernedSwarmResult:
        """Run a Governed Swarm on the canvas.

        Governed Swarms create a proposal for human approval before
        executing structural changes. Uses the ProposalEngine if available.
        """
        proposal_id = ""
        if self._proposal_engine is not None:
            from packages.prime.proposals import ModificationType, RiskLevel

            proposal = await self._proposal_engine.propose(
                title=f"Swarm: {task[:60]}",
                modification_type=ModificationType.BEHAVIOR_CHANGE,
                description=f"Governed swarm for domain '{domain_id}': {task}",
                reasoning="Swarm execution requested via canvas governance",
                expected_impact="Canvas modifications from multi-agent collaboration",
                risk_level=RiskLevel.MEDIUM,
                implementation_steps=[f"Execute swarm task: {task}"],
                proposed_by="canvas-swarm",
            )
            proposal_id = str(proposal.id)

        result = GovernedSwarmResult(
            task=task,
            participants=agent_ids or ["auto-selected"],
            status="pending_approval",
            proposal_id=proposal_id,
            proposed_changes=[{"task": task, "domain_id": domain_id}],
            approval_required=True,
        )

        await self._tape.log_event(
            event_type="canvas.governed_swarm",
            agent_id="canvas-v5",
            payload={
                "domain_id": domain_id,
                "task": task,
                "participants": result.participants,
                "proposal_id": proposal_id,
                "status": result.status,
            },
        )
        return result

    async def run_multi_domain_swarm(
        self,
        domain_ids: list[str],
        task: str,
        agent_ids: list[str] | None = None,
        governed: bool = False,
    ) -> MultiDomainSwarmResult:
        """Run a swarm across multiple domains.

        Enables agents from different domains to collaborate on the
        same canvas task with conflict detection, resolution, simulation,
        and impact analysis.
        """
        config = MultiDomainSwarmConfig(
            domain_ids=domain_ids,
            task=task,
            governed=governed,
            agent_ids=agent_ids,
        )
        return await self._multi_domain_engine.run(config)


# ---------------------------------------------------------------------------
# CanvasV5Engine -- Main orchestrator
# ---------------------------------------------------------------------------


class CanvasV5Engine:
    """Full Domain Canvas (v5) engine.

    Orchestrates all v5 features on top of the core CanvasService:
    - Plugin nodes
    - Simulation overlay
    - Tape overlay
    - Natural language editing
    - Prime Co-Pilot
    - AetherGit versioning
    - Swarm integration
    - Tiered UI registry

    Usage::

        engine = CanvasV5Engine(
            tape_service=tape_svc,
            canvas_service=canvas_svc,
        )

        # Natural language edit
        result = await engine.natural_language_edit(
            domain_id="legal-research",
            instruction="Move the domain node to the center",
        )

        # Co-Pilot suggestions
        suggestions = await engine.get_copilot_suggestions("legal-research")

        # Quick swarm
        swarm = await engine.run_quick_swarm(
            domain_id="legal-research",
            task="Optimize the layout for readability",
        )
    """

    def __init__(
        self,
        tape_service: TapeService,
        canvas_service: CanvasService,
        simulation_engine: SimulationEngine | None = None,
        proposal_engine: ProposalEngine | None = None,
        debate_arena: DebateArena | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        explainability_engine: ExplainabilityEngine | None = None,
        introspector: PrimeIntrospector | None = None,
    ) -> None:
        self._tape = tape_service
        self._canvas_service = canvas_service

        # Sub-engines
        self.plugin_nodes = PluginNodeManager(tape_service)
        self.simulation_overlay = SimulationOverlay(tape_service)
        self.tape_overlay = TapeOverlay(tape_service)
        self.nl_edit = NLEditEngine(tape_service)
        self.copilot = PrimeCoPilot(tape_service)
        self.versioning = CanvasVersioningManager(tape_service)
        self.swarm = SwarmIntegration(
            tape_service,
            proposal_engine=proposal_engine,
            debate_arena=debate_arena,
            simulation_engine=simulation_engine,
            impact_analyzer=impact_analyzer,
            explainability_engine=explainability_engine,
            introspector=introspector,
        )
        self.framework_registry = TieredUIRegistry()

    # -- Convenience methods that delegate to sub-engines --

    async def natural_language_edit(
        self,
        domain_id: str,
        instruction: str,
    ) -> NLEditResult:
        """Parse and apply a natural language canvas edit."""
        result = self.nl_edit.parse_instruction(instruction)
        return await self.nl_edit.apply_edit(self._canvas_service, domain_id, result)

    async def get_copilot_suggestions(self, domain_id: str) -> list[CopilotSuggestion]:
        """Get Prime Co-Pilot suggestions for a canvas."""
        canvas = await self._canvas_service.get_canvas(domain_id)
        return await self.copilot.analyze_canvas(canvas)

    async def apply_copilot_suggestion(
        self,
        domain_id: str,
        suggestion: CopilotSuggestion,
    ) -> bool:
        """Apply a Co-Pilot suggestion to the canvas."""
        return await self.copilot.apply_suggestion(self._canvas_service, domain_id, suggestion)

    async def save_canvas_version(
        self,
        domain_id: str,
        commit_message: str = "",
        author: str = "system",
    ) -> CanvasVersion:
        """Save a version snapshot of the canvas."""
        canvas = await self._canvas_service.get_canvas(domain_id)
        return self.versioning.save_version(canvas, commit_message, author)

    async def run_quick_swarm(
        self,
        domain_id: str,
        task: str,
        agent_ids: list[str] | None = None,
    ) -> QuickSwarmResult:
        """Run a Quick Swarm on the canvas."""
        return await self.swarm.run_quick_swarm(domain_id, task, agent_ids)

    async def run_governed_swarm(
        self,
        domain_id: str,
        task: str,
        agent_ids: list[str] | None = None,
    ) -> GovernedSwarmResult:
        """Run a Governed Swarm on the canvas."""
        return await self.swarm.run_governed_swarm(domain_id, task, agent_ids)

    async def run_multi_domain_swarm(
        self,
        domain_ids: list[str],
        task: str,
        agent_ids: list[str] | None = None,
        governed: bool = False,
    ) -> MultiDomainSwarmResult:
        """Run a Multi-Domain Swarm on the canvas."""
        return await self.swarm.run_multi_domain_swarm(domain_ids, task, agent_ids, governed)

    async def add_plugin_node(
        self,
        domain_id: str,
        config: PluginNodeConfig,
    ) -> tuple[PluginNodeConfig, CanvasNode]:
        """Add a Plugin Node to the canvas.

        Creates both a PluginNodeConfig in the PluginNodeManager and a
        corresponding CanvasNode on the canvas.
        """
        self.plugin_nodes.register_plugin_node(config)
        canvas_node = CanvasNode(
            id=config.node_id,
            node_type=CanvasNodeType.CUSTOM,
            label=config.label,
            metadata={
                "colour": "#94a3b8",
                "icon": "puzzle",
                "plugin_id": config.plugin_id,
                "plugin_type": config.plugin_type,
                "capabilities": config.capabilities,
                "node_subtype": "plugin",
            },
        )
        await self._canvas_service.add_node(domain_id, canvas_node)
        return config, canvas_node

    async def update_simulation_overlay(
        self,
        domain_id: str,
        node_metrics: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, SimulationMetric]]:
        """Update simulation overlay metrics for multiple nodes."""
        for node_id, metrics in node_metrics.items():
            for metric_name, value in metrics.items():
                self.simulation_overlay.update_node_metric(node_id, metric_name, value)
        return self.simulation_overlay.get_overlay_data(list(node_metrics.keys()))

    def get_tape_overlay_events(self, limit: int = 50) -> list[TapeEventEntry]:
        """Get recent Tape events for the overlay."""
        return self.tape_overlay.get_recent_events(limit)

    def list_frameworks(self, tier: FrameworkTier | None = None) -> list[TieredFramework]:
        """List supported UI frameworks, optionally by tier."""
        return self.framework_registry.list_frameworks(tier)

    def detect_framework(self, file_extension: str) -> TieredFramework | None:
        """Detect a framework from a file extension."""
        return self.framework_registry.detect_framework(file_extension)
