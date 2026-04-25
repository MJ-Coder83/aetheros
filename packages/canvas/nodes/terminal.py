"""Terminal Node — Visual TUI Layout Editor with AI co-pilot support.

A TerminalNode represents a TUI (Terminal User Interface) application
embedded in the Domain Canvas.  It provides:

1. **Visual TUI Layout Editor** — drag-and-drop widget placement on a
   character-grid canvas that maps directly to TUI framework code.

2. **Framework code generation** — bidirectional sync between the visual
   layout and runnable code for:
   - Python / Textual   (``textual``)
   - Python / Rich      (``rich``)
   - Go / Bubble Tea    (``bubbletea``)
   - Rust / Ratatui     (``ratatui``)
   - Node / Blessed     (``blessed``)

3. **AI co-pilot** — natural language layout suggestions powered by the
   LLM integration layer.  When ``USE_REAL_LLM=true`` is set the co-pilot
   uses DSPy; otherwise it falls back to heuristic rule-based suggestions.

4. **Tape logging** — every structural change and co-pilot interaction is
   appended to the Tape for full auditability.

Architecture::

    TerminalNode
    ├── add_widget()             — Place a widget on the grid
    ├── remove_widget()          — Remove a widget by ID
    ├── move_widget()            — Reposition a widget
    ├── resize_widget()          — Resize a widget
    ├── generate_code()          — Render the layout to framework source code
    ├── sync_from_code()         — Parse source code back into widget layout
    ├── suggest_layout()         — AI co-pilot layout suggestion
    ├── apply_suggestion()       — Accept a co-pilot suggestion
    └── snapshot()               — Export the full node state

Usage::

    node = TerminalNode(
        node_id="tui-dashboard",
        label="Dashboard TUI",
        framework=TUIFramework.TEXTUAL,
        tape_service=tape_svc,
        cols=120,
        rows=40,
    )

    node.add_widget(TUIWidget(
        widget_id="header",
        widget_type=TUIWidgetType.HEADER,
        label="My App",
        col=0, row=0, width=120, height=3,
    ))

    code = node.generate_code()
    suggestion = await node.suggest_layout("Add a data table and a status bar")
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from packages.llm import get_llm_provider, is_llm_enabled
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TUIFramework(StrEnum):
    """Supported TUI frameworks for code generation."""

    TEXTUAL = "textual"  # Python / Textual
    RICH = "rich"  # Python / Rich
    BUBBLETEA = "bubbletea"  # Go / Bubble Tea
    RATATUI = "ratatui"  # Rust / Ratatui
    BLESSED = "blessed"  # Node.js / Blessed
    GENERIC = "generic"  # Framework-agnostic pseudocode


class TUIWidgetType(StrEnum):
    """Visual widget types available in the TUI Layout Editor."""

    HEADER = "header"
    FOOTER = "footer"
    SIDEBAR = "sidebar"
    PANEL = "panel"
    TABLE = "table"
    INPUT = "input"
    BUTTON = "button"
    PROGRESS = "progress"
    LOG = "log"
    TREE = "tree"
    TABS = "tabs"
    STATUSBAR = "statusbar"
    DIVIDER = "divider"
    TEXT = "text"
    CUSTOM = "custom"


class SuggestionStatus(StrEnum):
    """Lifecycle status of a co-pilot layout suggestion."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TUIWidget(BaseModel):
    """A single widget on the TUI canvas grid.

    All dimensions are in terminal character units (columns / rows).
    ``col`` and ``row`` are zero-based top-left anchors.
    """

    widget_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    widget_type: TUIWidgetType = TUIWidgetType.PANEL
    label: str = ""
    col: int = 0  # x-anchor (character columns from left)
    row: int = 0  # y-anchor (character rows from top)
    width: int = 20  # width in columns
    height: int = 5  # height in rows
    style: dict[str, object] = Field(default_factory=dict)
    properties: dict[str, object] = Field(default_factory=dict)

    @property
    def right(self) -> int:
        """Exclusive right column."""
        return self.col + self.width

    @property
    def bottom(self) -> int:
        """Exclusive bottom row."""
        return self.row + self.height

    def overlaps(self, other: TUIWidget) -> bool:
        """Return True if this widget overlaps with ``other``."""
        return (
            self.col < other.right
            and self.right > other.col
            and self.row < other.bottom
            and self.bottom > other.row
        )

    def fits_in(self, cols: int, rows: int) -> bool:
        """Return True if this widget fits in a grid of ``cols`` x ``rows``."""
        return self.col >= 0 and self.row >= 0 and self.right <= cols and self.bottom <= rows


class LayoutSuggestion(BaseModel):
    """A layout suggestion produced by the AI co-pilot."""

    suggestion_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    prompt: str
    description: str
    widgets: list[TUIWidget] = Field(default_factory=list)
    rationale: str = ""
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TerminalNodeSnapshot(BaseModel):
    """Point-in-time snapshot of a TerminalNode's complete state."""

    node_id: str
    label: str
    framework: TUIFramework
    cols: int
    rows: int
    widgets: list[TUIWidget]
    suggestions: list[LayoutSuggestion]
    created_at: datetime
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Overlap and bounds errors
# ---------------------------------------------------------------------------


class TerminalNodeError(Exception):
    """Base exception for TerminalNode operations."""


class WidgetOverlapError(TerminalNodeError):
    """Raised when a widget placement would overlap an existing widget."""


class WidgetOutOfBoundsError(TerminalNodeError):
    """Raised when a widget placement is outside the grid boundaries."""


class WidgetNotFoundError(TerminalNodeError):
    """Raised when a requested widget does not exist."""


# ---------------------------------------------------------------------------
# TerminalNode
# ---------------------------------------------------------------------------


class TerminalNode:
    """Visual TUI Layout Editor canvas node with AI co-pilot.

    The node maintains a character-grid (``cols`` x ``rows``) on which
    ``TUIWidget`` objects are placed.  All mutations are logged to the Tape.

    Parameters
    ----------
    node_id:
        Unique identifier for this node on the canvas.
    label:
        Human-readable display name.
    framework:
        Target TUI framework for code generation.
    tape_service:
        Shared Tape service for audit logging.
    cols:
        Grid width in terminal character columns (default 80).
    rows:
        Grid height in terminal character rows (default 24).
    """

    def __init__(
        self,
        node_id: str,
        label: str,
        framework: TUIFramework,
        tape_service: TapeService,
        cols: int = 80,
        rows: int = 24,
    ) -> None:
        self.node_id = node_id
        self.label = label
        self.framework = framework
        self.cols = cols
        self.rows = rows
        self._tape = tape_service
        self._widgets: dict[str, TUIWidget] = {}
        self._suggestions: list[LayoutSuggestion] = []
        self._created_at: datetime = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Widget management
    # ------------------------------------------------------------------

    def add_widget(self, widget: TUIWidget, *, allow_overlap: bool = False) -> TUIWidget:
        """Place a widget on the grid.

        Parameters
        ----------
        widget:
            The widget to add.  ``widget_id`` must be unique within the node.
        allow_overlap:
            When ``True``, skip the overlap check.  Useful for layered or
            decorative widgets.  Default ``False``.

        Raises
        ------
        WidgetOutOfBoundsError
            If the widget extends beyond the grid boundary.
        WidgetOverlapError
            If the widget overlaps an existing widget (and ``allow_overlap``
            is ``False``).
        """
        if not widget.fits_in(self.cols, self.rows):
            raise WidgetOutOfBoundsError(
                f"Widget '{widget.widget_id}' ({widget.col},{widget.row} "
                f"+{widget.width}x{widget.height}) exceeds grid "
                f"{self.cols}x{self.rows}"
            )
        if not allow_overlap:
            for existing in self._widgets.values():
                if widget.overlaps(existing):
                    raise WidgetOverlapError(
                        f"Widget '{widget.widget_id}' overlaps "
                        f"existing widget '{existing.widget_id}'"
                    )
        self._widgets[widget.widget_id] = widget
        return widget

    def remove_widget(self, widget_id: str) -> TUIWidget:
        """Remove a widget by ID.

        Raises
        ------
        WidgetNotFoundError
            If no widget with ``widget_id`` exists.
        """
        if widget_id not in self._widgets:
            raise WidgetNotFoundError(f"Widget '{widget_id}' not found")
        return self._widgets.pop(widget_id)

    def move_widget(self, widget_id: str, col: int, row: int) -> TUIWidget:
        """Reposition a widget.

        Raises
        ------
        WidgetNotFoundError
            If no widget with ``widget_id`` exists.
        WidgetOutOfBoundsError
            If the new position is out of bounds.
        WidgetOverlapError
            If the new position overlaps another widget.
        """
        widget = self._get_widget(widget_id)
        updated = widget.model_copy(update={"col": col, "row": row})
        if not updated.fits_in(self.cols, self.rows):
            raise WidgetOutOfBoundsError(
                f"Widget '{widget_id}' at ({col},{row}) exceeds grid {self.cols}x{self.rows}"
            )
        for wid, existing in self._widgets.items():
            if wid != widget_id and updated.overlaps(existing):
                raise WidgetOverlapError(f"Widget '{widget_id}' at ({col},{row}) overlaps '{wid}'")
        self._widgets[widget_id] = updated
        return updated

    def resize_widget(self, widget_id: str, width: int, height: int) -> TUIWidget:
        """Resize a widget.

        Raises
        ------
        WidgetNotFoundError / WidgetOutOfBoundsError / WidgetOverlapError
            As per ``move_widget``.
        """
        widget = self._get_widget(widget_id)
        updated = widget.model_copy(update={"width": width, "height": height})
        if not updated.fits_in(self.cols, self.rows):
            raise WidgetOutOfBoundsError(
                f"Widget '{widget_id}' resized to ({width}x{height}) exceeds grid"
            )
        for wid, existing in self._widgets.items():
            if wid != widget_id and updated.overlaps(existing):
                raise WidgetOverlapError(f"Widget '{widget_id}' resized overlaps '{wid}'")
        self._widgets[widget_id] = updated
        return updated

    def get_widget(self, widget_id: str) -> TUIWidget | None:
        """Return the widget with ``widget_id``, or ``None``."""
        return self._widgets.get(widget_id)

    @property
    def widgets(self) -> list[TUIWidget]:
        """All widgets ordered by (row, col)."""
        return sorted(self._widgets.values(), key=lambda w: (w.row, w.col))

    @property
    def widget_count(self) -> int:
        return len(self._widgets)

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def generate_code(self) -> str:
        """Render the current layout to framework-specific source code.

        Returns a complete, runnable stub for the chosen ``framework`` that
        reflects the current widget placements.

        Returns
        -------
        str
            Source code string.
        """
        match self.framework:
            case TUIFramework.TEXTUAL:
                return self._gen_textual()
            case TUIFramework.RICH:
                return self._gen_rich()
            case TUIFramework.BUBBLETEA:
                return self._gen_bubbletea()
            case TUIFramework.RATATUI:
                return self._gen_ratatui()
            case TUIFramework.BLESSED:
                return self._gen_blessed()
            case _:
                return self._gen_generic()

    def sync_from_code(self, code: str, framework: TUIFramework | None = None) -> list[TUIWidget]:
        """Parse source code and update the widget layout accordingly.

        This is a best-effort parser — it extracts widget declarations and
        maps them to ``TUIWidget`` objects with approximate positions.
        Unknown widgets are added as ``TUIWidgetType.CUSTOM``.

        Parameters
        ----------
        code:
            Source code string (must match ``self.framework`` or ``framework``).
        framework:
            Override the node's framework for parsing.  Defaults to
            ``self.framework``.

        Returns
        -------
        list[TUIWidget]
            The list of parsed (and now registered) widgets.
        """
        fw = framework or self.framework
        self._widgets.clear()
        widgets: list[TUIWidget] = []

        match fw:
            case TUIFramework.TEXTUAL:
                widgets = self._parse_textual(code)
            case TUIFramework.RICH:
                widgets = self._parse_rich(code)
            case _:
                widgets = self._parse_generic(code)

        for widget in widgets:
            self._widgets[widget.widget_id] = widget
        return widgets

    # ------------------------------------------------------------------
    # AI co-pilot
    # ------------------------------------------------------------------

    async def suggest_layout(self, prompt: str) -> LayoutSuggestion:
        """Generate a layout suggestion from a natural language prompt.

        When ``USE_REAL_LLM=true`` the co-pilot uses DSPy to generate
        widget suggestions.  Otherwise it falls back to heuristic rules.

        Parameters
        ----------
        prompt:
            Natural language description of the desired layout change.

        Returns
        -------
        LayoutSuggestion
            A pending suggestion ready for ``apply_suggestion()``.
        """
        if is_llm_enabled():
            suggestion = await self._llm_suggest(prompt)
        else:
            suggestion = self._heuristic_suggest(prompt)

        self._suggestions.append(suggestion)
        await self._tape.log_event(
            event_type="canvas.terminal.suggestion_created",
            agent_id="prime",
            payload={
                "node_id": self.node_id,
                "suggestion_id": suggestion.suggestion_id,
                "prompt": prompt,
                "widget_count": len(suggestion.widgets),
                "rationale": suggestion.rationale,
            },
        )
        return suggestion

    async def apply_suggestion(self, suggestion_id: str) -> list[TUIWidget]:
        """Accept and apply a pending layout suggestion.

        Clears all existing widgets and replaces them with the suggestion's
        widget set.

        Parameters
        ----------
        suggestion_id:
            The ID of the suggestion to apply.

        Returns
        -------
        list[TUIWidget]
            The newly placed widgets.

        Raises
        ------
        WidgetNotFoundError
            If no suggestion with ``suggestion_id`` exists.
        """
        suggestion = next((s for s in self._suggestions if s.suggestion_id == suggestion_id), None)
        if suggestion is None:
            raise WidgetNotFoundError(f"Suggestion '{suggestion_id}' not found")

        self._widgets.clear()
        placed: list[TUIWidget] = []
        for widget in suggestion.widgets:
            try:
                self.add_widget(widget, allow_overlap=False)
                placed.append(widget)
            except (WidgetOverlapError, WidgetOutOfBoundsError):
                # Skip widgets that can't be placed without conflict
                pass

        suggestion.status = SuggestionStatus.ACCEPTED
        await self._tape.log_event(
            event_type="canvas.terminal.suggestion_applied",
            agent_id="prime",
            payload={
                "node_id": self.node_id,
                "suggestion_id": suggestion_id,
                "widgets_placed": len(placed),
            },
        )
        return placed

    @property
    def suggestions(self) -> list[LayoutSuggestion]:
        """All suggestions (pending, accepted, rejected)."""
        return list(self._suggestions)

    # ------------------------------------------------------------------
    # Snapshot / export
    # ------------------------------------------------------------------

    def snapshot(self) -> TerminalNodeSnapshot:
        """Export the complete node state as an immutable snapshot."""
        return TerminalNodeSnapshot(
            node_id=self.node_id,
            label=self.label,
            framework=self.framework,
            cols=self.cols,
            rows=self.rows,
            widgets=list(self._widgets.values()),
            suggestions=list(self._suggestions),
            created_at=self._created_at,
        )

    # ------------------------------------------------------------------
    # Tape helpers
    # ------------------------------------------------------------------

    async def log_widget_added(self, widget: TUIWidget) -> None:
        """Log a widget addition to the Tape."""
        await self._tape.log_event(
            event_type="canvas.terminal.widget_added",
            agent_id="prime",
            payload={
                "node_id": self.node_id,
                "widget_id": widget.widget_id,
                "widget_type": widget.widget_type,
                "position": {"col": widget.col, "row": widget.row},
                "size": {"width": widget.width, "height": widget.height},
            },
        )

    async def log_widget_removed(self, widget_id: str) -> None:
        """Log a widget removal to the Tape."""
        await self._tape.log_event(
            event_type="canvas.terminal.widget_removed",
            agent_id="prime",
            payload={"node_id": self.node_id, "widget_id": widget_id},
        )

    # ------------------------------------------------------------------
    # Code generation internals
    # ------------------------------------------------------------------

    def _gen_textual(self) -> str:
        """Generate a Textual (Python) app stub."""
        lines = [
            "from textual.app import App, ComposeResult",
            "from textual.widgets import Header, Footer, DataTable, Input, Button, Log, TabbedContent",
            "from textual.containers import Horizontal, Vertical",
            "",
            "",
            f"class {self._class_name(self.label)}App(App):",
            f'    """Generated by InkosAI TerminalNode — {self.label}"""',
            "",
            '    CSS = """',
        ]
        for widget in self.widgets:
            lines.append(
                f"    #{widget.widget_id} {{"
                f" column: {widget.col}; row: {widget.row}; "
                f"width: {widget.width}; height: {widget.height}; }}"
            )
        lines += [
            '    """',
            "",
            "    def compose(self) -> ComposeResult:",
        ]
        if not self.widgets:
            lines.append("        yield Header()")
            lines.append("        yield Footer()")
        else:
            for widget in self.widgets:
                textual_cls = _TEXTUAL_WIDGET_MAP.get(widget.widget_type, "Static")
                label_arg = f'"{widget.label}"' if widget.label else '""'
                lines.append(f'        yield {textual_cls}({label_arg}, id="{widget.widget_id}")')
        lines += [
            "",
            "",
            "if __name__ == '__main__':",
            f"    {self._class_name(self.label)}App().run()",
        ]
        return "\n".join(lines)

    def _gen_rich(self) -> str:
        """Generate a Rich (Python) layout stub."""
        lines = [
            "from rich.console import Console",
            "from rich.layout import Layout",
            "from rich.panel import Panel",
            "from rich.live import Live",
            "",
            "console = Console()",
            "layout = Layout()",
            "",
        ]
        if not self.widgets:
            lines.append('layout.split_column(Layout(name="main"))')
        else:
            for widget in self.widgets:
                lines.append(
                    f'layout.add_split(Layout(name="{widget.widget_id}", size={widget.height}))'
                )
                lines.append(f'layout["{widget.widget_id}"].update(Panel("{widget.label}"))')
        lines += [
            "",
            "with Live(layout, console=console, screen=True):",
            "    input('Press Enter to exit...')",
        ]
        return "\n".join(lines)

    def _gen_bubbletea(self) -> str:
        """Generate a Bubble Tea (Go) model stub."""
        lines = [
            "package main",
            "",
            "import (",
            '    "fmt"',
            '    tea "github.com/charmbracelet/bubbletea"',
            ")",
            "",
            "type model struct {",
        ]
        for widget in self.widgets:
            lines.append(f"    {widget.widget_id} string // {widget.widget_type}: {widget.label}")
        lines += [
            "}",
            "",
            "func initialModel() model {",
            "    return model{",
        ]
        for widget in self.widgets:
            lines.append(f'        {widget.widget_id}: "{widget.label}",')
        lines += [
            "    }",
            "}",
            "",
            "func (m model) Init() tea.Cmd { return nil }",
            "",
            "func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {",
            "    switch msg := msg.(type) {",
            "    case tea.KeyMsg:",
            '        if msg.String() == "q" { return m, tea.Quit }',
            "    }",
            "    return m, nil",
            "}",
            "",
            "func (m model) View() string {",
            '    return fmt.Sprintf("' + "\\n".join(f"{w.label}" for w in self.widgets) + '")',
            "}",
            "",
            "func main() {",
            "    p := tea.NewProgram(initialModel())",
            "    if _, err := p.Run(); err != nil { panic(err) }",
            "}",
        ]
        return "\n".join(lines)

    def _gen_ratatui(self) -> str:
        """Generate a Ratatui (Rust) stub."""
        lines = [
            "use ratatui::{",
            "    backend::CrosstermBackend,",
            "    layout::{Constraint, Direction, Layout},",
            "    widgets::{Block, Borders, Paragraph},",
            "    Terminal,",
            "};",
            "use std::io;",
            "",
            "fn main() -> io::Result<()> {",
            "    let backend = CrosstermBackend::new(io::stdout());",
            "    let mut terminal = Terminal::new(backend)?;",
            "    terminal.draw(|f| {",
        ]
        if self.widgets:
            constraints = ", ".join(f"Constraint::Length({w.height})" for w in self.widgets)
            lines.append(
                f"        let chunks = Layout::default()"
                f".direction(Direction::Vertical)"
                f".constraints([{constraints}])"
                f".split(f.area());"
            )
            for idx, widget in enumerate(self.widgets):
                lines.append(
                    f"        let block_{idx} = Block::default()"
                    f'.title("{widget.label}").borders(Borders::ALL);'
                )
                lines.append(f"        f.render_widget(block_{idx}, chunks[{idx}]);")
        lines += ["    })?;", "    Ok(())", "}"]
        return "\n".join(lines)

    def _gen_blessed(self) -> str:
        """Generate a Blessed (Node.js) stub."""
        lines = [
            "const blessed = require('blessed');",
            "",
            "const screen = blessed.screen({ smartCSR: true });",
            f"screen.title = '{self.label}';",
            "",
        ]
        for widget in self.widgets:
            blessed_type = _BLESSED_WIDGET_MAP.get(widget.widget_type, "box")
            lines.append(f"const {widget.widget_id} = blessed.{blessed_type}({{")
            lines.append(f"  top: {widget.row},")
            lines.append(f"  left: {widget.col},")
            lines.append(f"  width: {widget.width},")
            lines.append(f"  height: {widget.height},")
            lines.append(f"  content: '{widget.label}',")
            lines.append("  border: { type: 'line' },")
            lines.append("});")
            lines.append(f"screen.append({widget.widget_id});")
            lines.append("")
        lines += [
            "screen.key(['q', 'C-c'], () => process.exit(0));",
            "screen.render();",
        ]
        return "\n".join(lines)

    def _gen_generic(self) -> str:
        """Generate framework-agnostic pseudocode."""
        lines = [f"# TUI Layout: {self.label} ({self.cols}x{self.rows})", ""]
        for widget in self.widgets:
            lines.append(
                f"WIDGET {widget.widget_type.upper()} '{widget.label}' "
                f"at ({widget.col},{widget.row}) size {widget.width}x{widget.height}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Code parsing internals
    # ------------------------------------------------------------------

    def _parse_textual(self, code: str) -> list[TUIWidget]:
        """Extract widget declarations from Textual CSS + compose body."""
        widgets: list[TUIWidget] = []
        # Parse CSS block positions: #widget_id { column: X; row: Y; width: W; height: H; }
        css_pattern = re.compile(
            r"#(\w+)\s*\{[^}]*column:\s*(\d+)[^}]*row:\s*(\d+)[^}]*"
            r"width:\s*(\d+)[^}]*height:\s*(\d+)[^}]*\}"
        )
        for m in css_pattern.finditer(code):
            widget_id, col, row, width, height = m.group(1, 2, 3, 4, 5)
            widgets.append(
                TUIWidget(
                    widget_id=widget_id,
                    widget_type=TUIWidgetType.PANEL,
                    col=int(col),
                    row=int(row),
                    width=int(width),
                    height=int(height),
                )
            )
        return widgets

    def _parse_rich(self, code: str) -> list[TUIWidget]:
        """Extract layout splits from Rich Layout code."""
        widgets: list[TUIWidget] = []
        split_pattern = re.compile(r'Layout\(name="(\w+)"(?:,\s*size=(\d+))?\)')
        row = 0
        for m in split_pattern.finditer(code):
            name = m.group(1)
            height = int(m.group(2)) if m.group(2) else 5
            widgets.append(
                TUIWidget(
                    widget_id=name,
                    widget_type=TUIWidgetType.PANEL,
                    col=0,
                    row=row,
                    width=self.cols,
                    height=height,
                )
            )
            row += height
        return widgets

    def _parse_generic(self, code: str) -> list[TUIWidget]:
        """Parse generic pseudocode: WIDGET TYPE 'label' at (col,row) size WxH."""
        widgets: list[TUIWidget] = []
        pattern = re.compile(
            r"WIDGET\s+(\w+)\s+'([^']*)'\s+at\s+\((\d+),(\d+)\)\s+size\s+(\d+)x(\d+)",
            re.IGNORECASE,
        )
        for m in pattern.finditer(code):
            wtype_str, label, col, row, width, height = m.groups()
            try:
                wtype = TUIWidgetType(wtype_str.lower())
            except ValueError:
                wtype = TUIWidgetType.CUSTOM
            widgets.append(
                TUIWidget(
                    widget_id=f"w{len(widgets)}",
                    widget_type=wtype,
                    label=label,
                    col=int(col),
                    row=int(row),
                    width=int(width),
                    height=int(height),
                )
            )
        return widgets

    # ------------------------------------------------------------------
    # AI co-pilot internals
    # ------------------------------------------------------------------

    async def _llm_suggest(self, prompt: str) -> LayoutSuggestion:
        """Generate a suggestion using the LLM provider."""
        llm = get_llm_provider()
        context = (
            f"TUI layout editor. Grid: {self.cols} cols x {self.rows} rows. "
            f"Framework: {self.framework}. "
            f"Current widgets: {[w.label or w.widget_type for w in self.widgets]}. "
            f"User request: {prompt}. "
            "Respond with: DESCRIPTION: <one line>. RATIONALE: <one line>. "
            "WIDGETS: <comma-separated list of TYPE:label:col:row:width:height>."
        )
        response = await llm.generate(context, max_tokens=300)
        return self._parse_llm_response(prompt, response)

    def _parse_llm_response(self, prompt: str, response: str) -> LayoutSuggestion:
        """Parse structured LLM response into a LayoutSuggestion."""
        description = ""
        rationale = ""
        widgets: list[TUIWidget] = []

        for line in response.splitlines():
            if line.startswith("DESCRIPTION:"):
                description = line.removeprefix("DESCRIPTION:").strip()
            elif line.startswith("RATIONALE:"):
                rationale = line.removeprefix("RATIONALE:").strip()
            elif line.startswith("WIDGETS:"):
                widget_defs = line.removeprefix("WIDGETS:").strip()
                for widget_def in widget_defs.split(","):
                    parts = widget_def.strip().split(":")
                    if len(parts) >= 6:
                        try:
                            wtype = TUIWidgetType(parts[0].strip().lower())
                            label = parts[1].strip()
                            col, row, width, height = (int(p.strip()) for p in parts[2:6])
                            widgets.append(
                                TUIWidget(
                                    widget_type=wtype,
                                    label=label,
                                    col=col,
                                    row=row,
                                    width=width,
                                    height=height,
                                )
                            )
                        except (ValueError, IndexError):
                            pass

        if not description:
            description = f"Layout suggestion for: {prompt}"
        if not rationale:
            rationale = "Generated by LLM co-pilot"

        return LayoutSuggestion(
            prompt=prompt,
            description=description,
            rationale=rationale,
            widgets=widgets,
        )

    def _heuristic_suggest(self, prompt: str) -> LayoutSuggestion:
        """Rule-based layout suggestion when LLM is not enabled.

        Parses keywords from the prompt and returns a sensible default
        widget arrangement.
        """
        q = prompt.lower()
        widgets: list[TUIWidget] = []
        description = f"Heuristic layout for: {prompt}"
        rationale = "Keyword-based suggestion (LLM disabled)"

        # Always place a header at the top
        if True:  # always add a header
            widgets.append(
                TUIWidget(
                    widget_id="header",
                    widget_type=TUIWidgetType.HEADER,
                    label=self.label,
                    col=0,
                    row=0,
                    width=self.cols,
                    height=3,
                )
            )

        body_row = 3
        body_height = self.rows - 6  # leave room for header + statusbar

        if "table" in q or "data" in q or "list" in q:
            widgets.append(
                TUIWidget(
                    widget_id="data_table",
                    widget_type=TUIWidgetType.TABLE,
                    label="Data",
                    col=0,
                    row=body_row,
                    width=self.cols,
                    height=body_height,
                )
            )
            description = "Header + data table + status bar layout"
        elif "sidebar" in q:
            sidebar_w = self.cols // 4
            widgets.append(
                TUIWidget(
                    widget_id="sidebar",
                    widget_type=TUIWidgetType.SIDEBAR,
                    label="Navigation",
                    col=0,
                    row=body_row,
                    width=sidebar_w,
                    height=body_height,
                )
            )
            widgets.append(
                TUIWidget(
                    widget_id="main_panel",
                    widget_type=TUIWidgetType.PANEL,
                    label="Main",
                    col=sidebar_w,
                    row=body_row,
                    width=self.cols - sidebar_w,
                    height=body_height,
                )
            )
            description = "Header + sidebar + main panel + status bar layout"
        elif "log" in q:
            panel_h = body_height // 2
            widgets.append(
                TUIWidget(
                    widget_id="main_panel",
                    widget_type=TUIWidgetType.PANEL,
                    label="Main",
                    col=0,
                    row=body_row,
                    width=self.cols,
                    height=panel_h,
                )
            )
            widgets.append(
                TUIWidget(
                    widget_id="log_view",
                    widget_type=TUIWidgetType.LOG,
                    label="Log",
                    col=0,
                    row=body_row + panel_h,
                    width=self.cols,
                    height=body_height - panel_h,
                )
            )
            description = "Header + panel + log view + status bar layout"
        elif "input" in q or "form" in q:
            widgets.append(
                TUIWidget(
                    widget_id="form_panel",
                    widget_type=TUIWidgetType.PANEL,
                    label="Form",
                    col=0,
                    row=body_row,
                    width=self.cols,
                    height=body_height - 4,
                )
            )
            widgets.append(
                TUIWidget(
                    widget_id="input_field",
                    widget_type=TUIWidgetType.INPUT,
                    label="Input",
                    col=2,
                    row=body_row + 1,
                    width=self.cols - 4,
                    height=3,
                )
            )
            description = "Header + input form + status bar layout"
        else:
            widgets.append(
                TUIWidget(
                    widget_id="main_panel",
                    widget_type=TUIWidgetType.PANEL,
                    label="Main",
                    col=0,
                    row=body_row,
                    width=self.cols,
                    height=body_height,
                )
            )
            description = "Header + main panel + status bar layout"

        # Status bar at the bottom
        statusbar_row = self.rows - 3
        if statusbar_row > body_row:
            widgets.append(
                TUIWidget(
                    widget_id="statusbar",
                    widget_type=TUIWidgetType.STATUSBAR,
                    label="Ready",
                    col=0,
                    row=statusbar_row,
                    width=self.cols,
                    height=3,
                )
            )

        return LayoutSuggestion(
            prompt=prompt,
            description=description,
            rationale=rationale,
            widgets=widgets,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _get_widget(self, widget_id: str) -> TUIWidget:
        """Return a widget by ID or raise WidgetNotFoundError."""
        widget = self._widgets.get(widget_id)
        if widget is None:
            raise WidgetNotFoundError(f"Widget '{widget_id}' not found")
        return widget

    @staticmethod
    def _class_name(label: str) -> str:
        """Convert a label to a PascalCase class name.

        Non-alphanumeric characters are treated as word separators.
        """
        # Replace any non-alphanumeric char with a space, then title-case each word
        normalised = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
        return "".join(word.capitalize() for word in normalised.split())


# ---------------------------------------------------------------------------
# Framework widget type maps
# ---------------------------------------------------------------------------

_TEXTUAL_WIDGET_MAP: dict[TUIWidgetType, str] = {
    TUIWidgetType.HEADER: "Header",
    TUIWidgetType.FOOTER: "Footer",
    TUIWidgetType.TABLE: "DataTable",
    TUIWidgetType.INPUT: "Input",
    TUIWidgetType.BUTTON: "Button",
    TUIWidgetType.LOG: "Log",
    TUIWidgetType.TREE: "Tree",
    TUIWidgetType.TABS: "TabbedContent",
    TUIWidgetType.PROGRESS: "ProgressBar",
    TUIWidgetType.PANEL: "Static",
    TUIWidgetType.TEXT: "Static",
    TUIWidgetType.DIVIDER: "Rule",
    TUIWidgetType.STATUSBAR: "Footer",
    TUIWidgetType.SIDEBAR: "Static",
    TUIWidgetType.CUSTOM: "Widget",
}

_BLESSED_WIDGET_MAP: dict[TUIWidgetType, str] = {
    TUIWidgetType.HEADER: "box",
    TUIWidgetType.FOOTER: "box",
    TUIWidgetType.TABLE: "listtable",
    TUIWidgetType.INPUT: "textbox",
    TUIWidgetType.BUTTON: "button",
    TUIWidgetType.LOG: "log",
    TUIWidgetType.TREE: "treeview",
    TUIWidgetType.TABS: "box",
    TUIWidgetType.PROGRESS: "progressbar",
    TUIWidgetType.PANEL: "box",
    TUIWidgetType.TEXT: "text",
    TUIWidgetType.DIVIDER: "line",
    TUIWidgetType.STATUSBAR: "box",
    TUIWidgetType.SIDEBAR: "box",
    TUIWidgetType.CUSTOM: "box",
}
