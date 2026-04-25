"""Tests for TerminalNode — Visual TUI Layout Editor (Agent 3, Domain Canvas part 3/4).

Covers:
- TUIWidget data model (bounds, overlap, properties)
- TerminalNode widget management (add, remove, move, resize)
- Error cases (out-of-bounds, overlap, not-found)
- Code generation for all 6 frameworks (Textual, Rich, Bubble Tea, Ratatui, Blessed, Generic)
- Code parsing (Textual CSS, Rich layout, Generic pseudocode)
- Heuristic AI co-pilot suggestions (all keyword branches)
- apply_suggestion() workflow
- Tape logging (widget_added, widget_removed, suggestion_created, suggestion_applied)
- Snapshot export
- Edge cases (empty node, single widget, resize conflict)
"""

from __future__ import annotations

import pytest

from packages.canvas.nodes.terminal import (
    LayoutSuggestion,
    SuggestionStatus,
    TerminalNode,
    TerminalNodeSnapshot,
    TUIFramework,
    TUIWidget,
    TUIWidgetType,
    WidgetNotFoundError,
    WidgetOutOfBoundsError,
    WidgetOverlapError,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def node(tape_svc: TapeService) -> TerminalNode:
    return TerminalNode(
        node_id="test-node",
        label="Test TUI",
        framework=TUIFramework.TEXTUAL,
        tape_service=tape_svc,
        cols=80,
        rows=24,
    )


@pytest.fixture()
def header_widget() -> TUIWidget:
    return TUIWidget(
        widget_id="header",
        widget_type=TUIWidgetType.HEADER,
        label="My App",
        col=0, row=0, width=80, height=3,
    )


@pytest.fixture()
def body_widget() -> TUIWidget:
    return TUIWidget(
        widget_id="body",
        widget_type=TUIWidgetType.PANEL,
        label="Body",
        col=0, row=3, width=80, height=18,
    )


@pytest.fixture()
def footer_widget() -> TUIWidget:
    return TUIWidget(
        widget_id="footer",
        widget_type=TUIWidgetType.FOOTER,
        label="Footer",
        col=0, row=21, width=80, height=3,
    )


# ---------------------------------------------------------------------------
# TUIWidget model tests
# ---------------------------------------------------------------------------


class TestTUIWidget:
    def test_right_and_bottom(self) -> None:
        w = TUIWidget(widget_id="w", widget_type=TUIWidgetType.PANEL, col=5, row=3, width=20, height=10)
        assert w.right == 25
        assert w.bottom == 13

    def test_overlaps_true(self) -> None:
        a = TUIWidget(widget_id="a", widget_type=TUIWidgetType.PANEL, col=0, row=0, width=10, height=5)
        b = TUIWidget(widget_id="b", widget_type=TUIWidgetType.PANEL, col=5, row=2, width=10, height=5)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_overlaps_false_adjacent(self) -> None:
        a = TUIWidget(widget_id="a", widget_type=TUIWidgetType.PANEL, col=0, row=0, width=10, height=5)
        b = TUIWidget(widget_id="b", widget_type=TUIWidgetType.PANEL, col=10, row=0, width=10, height=5)
        assert not a.overlaps(b)

    def test_overlaps_false_vertical(self) -> None:
        a = TUIWidget(widget_id="a", widget_type=TUIWidgetType.PANEL, col=0, row=0, width=80, height=3)
        b = TUIWidget(widget_id="b", widget_type=TUIWidgetType.PANEL, col=0, row=3, width=80, height=18)
        assert not a.overlaps(b)

    def test_fits_in_true(self) -> None:
        w = TUIWidget(widget_id="w", widget_type=TUIWidgetType.PANEL, col=0, row=0, width=80, height=24)
        assert w.fits_in(80, 24)

    def test_fits_in_false_right(self) -> None:
        w = TUIWidget(widget_id="w", widget_type=TUIWidgetType.PANEL, col=75, row=0, width=10, height=5)
        assert not w.fits_in(80, 24)

    def test_fits_in_false_bottom(self) -> None:
        w = TUIWidget(widget_id="w", widget_type=TUIWidgetType.PANEL, col=0, row=22, width=10, height=5)
        assert not w.fits_in(80, 24)

    def test_defaults(self) -> None:
        w = TUIWidget(widget_id="w", widget_type=TUIWidgetType.CUSTOM)
        assert w.col == 0
        assert w.row == 0
        assert w.width == 20
        assert w.height == 5
        assert w.style == {}
        assert w.properties == {}


# ---------------------------------------------------------------------------
# TerminalNode widget management
# ---------------------------------------------------------------------------


class TestAddWidget:
    def test_add_widget_returns_widget(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        result = node.add_widget(header_widget)
        assert result is header_widget

    def test_add_widget_increases_count(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        assert node.widget_count == 1

    def test_add_multiple_non_overlapping(
        self,
        node: TerminalNode,
        header_widget: TUIWidget,
        body_widget: TUIWidget,
        footer_widget: TUIWidget,
    ) -> None:
        node.add_widget(header_widget)
        node.add_widget(body_widget)
        node.add_widget(footer_widget)
        assert node.widget_count == 3

    def test_add_out_of_bounds_raises(self, node: TerminalNode) -> None:
        oob = TUIWidget(widget_id="oob", widget_type=TUIWidgetType.PANEL, col=75, row=0, width=20, height=5)
        with pytest.raises(WidgetOutOfBoundsError):
            node.add_widget(oob)

    def test_add_overlapping_raises(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        overlap = TUIWidget(
            widget_id="overlap",
            widget_type=TUIWidgetType.PANEL,
            col=0, row=0, width=40, height=3,
        )
        with pytest.raises(WidgetOverlapError):
            node.add_widget(overlap)

    def test_add_overlapping_allowed(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        overlay = TUIWidget(
            widget_id="overlay",
            widget_type=TUIWidgetType.TEXT,
            col=0, row=0, width=40, height=3,
        )
        node.add_widget(overlay, allow_overlap=True)
        assert node.widget_count == 2


class TestRemoveWidget:
    def test_remove_existing_widget(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        removed = node.remove_widget("header")
        assert removed is header_widget
        assert node.widget_count == 0

    def test_remove_nonexistent_raises(self, node: TerminalNode) -> None:
        with pytest.raises(WidgetNotFoundError):
            node.remove_widget("missing")


class TestMoveWidget:
    def test_move_widget_updates_position(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        moved = node.move_widget("header", col=0, row=1)
        assert moved.row == 1

    def test_move_widget_out_of_bounds_raises(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        with pytest.raises(WidgetOutOfBoundsError):
            node.move_widget("header", col=0, row=22)  # 22 + 3 = 25 > 24

    def test_move_widget_overlap_raises(
        self,
        node: TerminalNode,
        header_widget: TUIWidget,
        body_widget: TUIWidget,
    ) -> None:
        node.add_widget(header_widget)
        node.add_widget(body_widget)
        with pytest.raises(WidgetOverlapError):
            node.move_widget("body", col=0, row=0)  # would overlap header

    def test_move_nonexistent_raises(self, node: TerminalNode) -> None:
        with pytest.raises(WidgetNotFoundError):
            node.move_widget("missing", col=0, row=0)


class TestResizeWidget:
    def test_resize_widget(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        resized = node.resize_widget("header", width=40, height=3)
        assert resized.width == 40

    def test_resize_out_of_bounds_raises(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        with pytest.raises(WidgetOutOfBoundsError):
            node.resize_widget("header", width=100, height=3)

    def test_resize_overlap_raises(
        self,
        node: TerminalNode,
        header_widget: TUIWidget,
        body_widget: TUIWidget,
    ) -> None:
        node.add_widget(header_widget)
        node.add_widget(body_widget)
        with pytest.raises(WidgetOverlapError):
            node.resize_widget("header", width=80, height=10)  # expands into body

    def test_resize_nonexistent_raises(self, node: TerminalNode) -> None:
        with pytest.raises(WidgetNotFoundError):
            node.resize_widget("missing", width=10, height=5)


class TestWidgetProperties:
    def test_get_widget_returns_none_for_missing(self, node: TerminalNode) -> None:
        assert node.get_widget("missing") is None

    def test_get_widget_returns_widget(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        assert node.get_widget("header") is header_widget

    def test_widgets_property_sorted_by_row_col(
        self,
        node: TerminalNode,
        footer_widget: TUIWidget,
        header_widget: TUIWidget,
        body_widget: TUIWidget,
    ) -> None:
        # Add out of order
        node.add_widget(footer_widget)
        node.add_widget(header_widget)
        node.add_widget(body_widget)
        rows = [w.row for w in node.widgets]
        assert rows == sorted(rows)


# ---------------------------------------------------------------------------
# Code generation tests
# ---------------------------------------------------------------------------


class TestGenerateCode:
    def test_textual_code_contains_app_class(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        code = node.generate_code()
        assert "App" in code
        assert "compose" in code

    def test_textual_code_contains_widget_id(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        code = node.generate_code()
        assert "header" in code

    def test_rich_code_generation(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        n = TerminalNode("n", "Rich App", TUIFramework.RICH, tape_svc)
        n.add_widget(header_widget)
        code = n.generate_code()
        assert "Layout" in code or "layout" in code

    def test_bubbletea_code_generation(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        n = TerminalNode("n", "Go App", TUIFramework.BUBBLETEA, tape_svc)
        n.add_widget(header_widget)
        code = n.generate_code()
        assert "package main" in code
        assert "bubbletea" in code

    def test_ratatui_code_generation(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        n = TerminalNode("n", "Rust App", TUIFramework.RATATUI, tape_svc)
        n.add_widget(header_widget)
        code = n.generate_code()
        assert "ratatui" in code

    def test_blessed_code_generation(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        n = TerminalNode("n", "Node App", TUIFramework.BLESSED, tape_svc)
        n.add_widget(header_widget)
        code = n.generate_code()
        assert "blessed" in code
        assert "screen" in code

    def test_generic_code_generation(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        n = TerminalNode("n", "Generic App", TUIFramework.GENERIC, tape_svc)
        n.add_widget(header_widget)
        code = n.generate_code()
        assert "WIDGET" in code
        assert "HEADER" in code

    def test_empty_node_generates_valid_code(self, node: TerminalNode) -> None:
        code = node.generate_code()
        assert isinstance(code, str)
        assert len(code) > 0

    def test_code_generation_all_frameworks_produce_strings(
        self, tape_svc: TapeService, header_widget: TUIWidget
    ) -> None:
        for fw in TUIFramework:
            n = TerminalNode("n", "App", fw, tape_svc)
            n.add_widget(header_widget, allow_overlap=True)
            code = n.generate_code()
            assert isinstance(code, str)
            assert len(code) > 0


# ---------------------------------------------------------------------------
# Code parsing tests
# ---------------------------------------------------------------------------


class TestSyncFromCode:
    def test_parse_generic_pseudocode(self, node: TerminalNode) -> None:
        code = (
            "WIDGET header 'My App' at (0,0) size 80x3\n"
            "WIDGET panel 'Body' at (0,3) size 80x18\n"
            "WIDGET statusbar 'Ready' at (0,21) size 80x3"
        )
        widgets = node.sync_from_code(code, framework=TUIFramework.GENERIC)
        assert len(widgets) == 3
        assert widgets[0].widget_type == TUIWidgetType.HEADER

    def test_parse_generic_unknown_type_becomes_custom(self, node: TerminalNode) -> None:
        code = "WIDGET unknowntype 'X' at (0,0) size 10x5"
        widgets = node.sync_from_code(code, framework=TUIFramework.GENERIC)
        assert len(widgets) == 1
        assert widgets[0].widget_type == TUIWidgetType.CUSTOM

    def test_parse_rich_layout(self, tape_svc: TapeService) -> None:
        n = TerminalNode("n", "App", TUIFramework.RICH, tape_svc)
        code = (
            'Layout(name="header", size=3)\n'
            'Layout(name="body", size=18)\n'
            'Layout(name="footer", size=3)\n'
        )
        widgets = n.sync_from_code(code, framework=TUIFramework.RICH)
        assert len(widgets) == 3
        assert widgets[0].widget_id == "header"
        assert widgets[1].row == 3
        assert widgets[2].row == 21

    def test_parse_textual_css(self, node: TerminalNode) -> None:
        code = (
            "#header { column: 0; row: 0; width: 80; height: 3; }\n"
            "#body { column: 0; row: 3; width: 80; height: 18; }\n"
        )
        widgets = node.sync_from_code(code, framework=TUIFramework.TEXTUAL)
        assert len(widgets) == 2
        assert widgets[0].widget_id == "header"

    def test_sync_clears_existing_widgets(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        assert node.widget_count == 1
        node.sync_from_code("", framework=TUIFramework.GENERIC)
        assert node.widget_count == 0


# ---------------------------------------------------------------------------
# AI co-pilot heuristic tests
# ---------------------------------------------------------------------------


class TestHeuristicSuggest:
    @pytest.mark.asyncio
    async def test_suggest_returns_layout_suggestion(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a data table")
        assert isinstance(suggestion, LayoutSuggestion)

    @pytest.mark.asyncio
    async def test_suggest_pending_status(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Show a table")
        assert suggestion.status == SuggestionStatus.PENDING

    @pytest.mark.asyncio
    async def test_suggest_table_layout(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a data table for logs")
        types = [w.widget_type for w in suggestion.widgets]
        assert TUIWidgetType.TABLE in types or TUIWidgetType.HEADER in types

    @pytest.mark.asyncio
    async def test_suggest_sidebar_layout(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a sidebar navigation")
        types = [w.widget_type for w in suggestion.widgets]
        assert TUIWidgetType.SIDEBAR in types

    @pytest.mark.asyncio
    async def test_suggest_log_layout(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a log view at the bottom")
        types = [w.widget_type for w in suggestion.widgets]
        assert TUIWidgetType.LOG in types

    @pytest.mark.asyncio
    async def test_suggest_input_form_layout(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add an input form")
        types = [w.widget_type for w in suggestion.widgets]
        assert TUIWidgetType.INPUT in types

    @pytest.mark.asyncio
    async def test_suggest_generic_layout(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Make it look nice")
        assert len(suggestion.widgets) > 0

    @pytest.mark.asyncio
    async def test_suggest_all_widgets_fit_in_grid(self, node: TerminalNode) -> None:
        for prompt in [
            "Show a table",
            "Add a sidebar",
            "Add a log view",
            "Add an input form",
            "Make it nice",
        ]:
            suggestion = await node.suggest_layout(prompt)
            for widget in suggestion.widgets:
                assert widget.fits_in(node.cols, node.rows), (
                    f"Widget {widget.widget_id!r} does not fit in {node.cols}x{node.rows}: "
                    f"({widget.col},{widget.row})+{widget.width}x{widget.height}"
                )

    @pytest.mark.asyncio
    async def test_suggest_stored_in_suggestions_list(self, node: TerminalNode) -> None:
        await node.suggest_layout("Add a table")
        assert len(node.suggestions) == 1

    @pytest.mark.asyncio
    async def test_suggest_description_non_empty(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("anything")
        assert suggestion.description != ""


# ---------------------------------------------------------------------------
# apply_suggestion() tests
# ---------------------------------------------------------------------------


class TestApplySuggestion:
    @pytest.mark.asyncio
    async def test_apply_suggestion_places_widgets(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a data table")
        placed = await node.apply_suggestion(suggestion.suggestion_id)
        assert len(placed) > 0
        assert node.widget_count > 0

    @pytest.mark.asyncio
    async def test_apply_suggestion_marks_accepted(self, node: TerminalNode) -> None:
        suggestion = await node.suggest_layout("Add a table")
        await node.apply_suggestion(suggestion.suggestion_id)
        assert suggestion.status == SuggestionStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_apply_suggestion_clears_existing_widgets(
        self, node: TerminalNode
    ) -> None:
        # Add a custom widget that won't collide with suggestion widget IDs
        custom = TUIWidget(
            widget_id="custom-only-widget",
            widget_type=TUIWidgetType.PANEL,
            label="Existing",
            col=10, row=10, width=10, height=5,
        )
        node.add_widget(custom)
        assert node.widget_count == 1
        suggestion = await node.suggest_layout("Replace with table layout")
        await node.apply_suggestion(suggestion.suggestion_id)
        # After applying, the original custom widget is gone (grid was cleared)
        assert node.get_widget("custom-only-widget") is None
        # Suggestion widgets were placed
        assert node.widget_count > 0

    @pytest.mark.asyncio
    async def test_apply_nonexistent_suggestion_raises(self, node: TerminalNode) -> None:
        with pytest.raises(WidgetNotFoundError):
            await node.apply_suggestion("nonexistent-id")


# ---------------------------------------------------------------------------
# Snapshot tests
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_snapshot_returns_terminal_node_snapshot(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        snap = node.snapshot()
        assert isinstance(snap, TerminalNodeSnapshot)

    def test_snapshot_contains_correct_metadata(
        self, node: TerminalNode
    ) -> None:
        snap = node.snapshot()
        assert snap.node_id == "test-node"
        assert snap.label == "Test TUI"
        assert snap.framework == TUIFramework.TEXTUAL
        assert snap.cols == 80
        assert snap.rows == 24

    def test_snapshot_contains_widgets(
        self, node: TerminalNode, header_widget: TUIWidget, body_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        node.add_widget(body_widget)
        snap = node.snapshot()
        assert len(snap.widgets) == 2

    def test_snapshot_is_immutable_copy(
        self, node: TerminalNode, header_widget: TUIWidget
    ) -> None:
        node.add_widget(header_widget)
        snap = node.snapshot()
        node.remove_widget("header")
        # Snapshot should still contain the widget
        assert len(snap.widgets) == 1


# ---------------------------------------------------------------------------
# Tape logging tests
# ---------------------------------------------------------------------------


class TestTapeLogging:
    @pytest.mark.asyncio
    async def test_widget_added_logged(
        self,
        node: TerminalNode,
        header_widget: TUIWidget,
        tape_svc: TapeService,
    ) -> None:
        node.add_widget(header_widget)
        await node.log_widget_added(header_widget)
        entries = await tape_svc.get_entries(event_type="canvas.terminal.widget_added")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_widget_removed_logged(
        self,
        node: TerminalNode,
        header_widget: TUIWidget,
        tape_svc: TapeService,
    ) -> None:
        node.add_widget(header_widget)
        await node.log_widget_removed("header")
        entries = await tape_svc.get_entries(event_type="canvas.terminal.widget_removed")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_suggestion_created_logged(
        self,
        node: TerminalNode,
        tape_svc: TapeService,
    ) -> None:
        await node.suggest_layout("Add a table")
        entries = await tape_svc.get_entries(event_type="canvas.terminal.suggestion_created")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_suggestion_applied_logged(
        self,
        node: TerminalNode,
        tape_svc: TapeService,
    ) -> None:
        suggestion = await node.suggest_layout("Add a table")
        await node.apply_suggestion(suggestion.suggestion_id)
        entries = await tape_svc.get_entries(event_type="canvas.terminal.suggestion_applied")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_suggestion_payload_contains_node_id(
        self,
        node: TerminalNode,
        tape_svc: TapeService,
    ) -> None:
        await node.suggest_layout("Add a sidebar")
        entries = await tape_svc.get_entries(event_type="canvas.terminal.suggestion_created")
        payload = entries[0].payload
        assert payload["node_id"] == "test-node"

    @pytest.mark.asyncio
    async def test_multiple_suggestions_log_multiple_events(
        self,
        node: TerminalNode,
        tape_svc: TapeService,
    ) -> None:
        await node.suggest_layout("Add a table")
        await node.suggest_layout("Add a sidebar")
        entries = await tape_svc.get_entries(event_type="canvas.terminal.suggestion_created")
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# TerminalNode class name helper
# ---------------------------------------------------------------------------


class TestClassNameHelper:
    def test_pascal_case_from_label(self) -> None:
        assert TerminalNode._class_name("my tui app") == "MyTuiApp"

    def test_strips_special_chars(self) -> None:
        assert TerminalNode._class_name("hello-world!") == "HelloWorld"

    def test_empty_label(self) -> None:
        assert TerminalNode._class_name("") == ""


# ---------------------------------------------------------------------------
# LLM response parser
# ---------------------------------------------------------------------------


class TestParseLLMResponse:
    def test_parse_valid_response(self, node: TerminalNode) -> None:
        response = (
            "DESCRIPTION: Header + table layout\n"
            "RATIONALE: Best for tabular data\n"
            "WIDGETS: header:Title:0:0:80:3, table:Data:0:3:80:18"
        )
        suggestion = node._parse_llm_response("Add a table", response)
        assert suggestion.description == "Header + table layout"
        assert suggestion.rationale == "Best for tabular data"
        assert len(suggestion.widgets) == 2

    def test_parse_empty_response_uses_defaults(self, node: TerminalNode) -> None:
        suggestion = node._parse_llm_response("Add a table", "")
        assert "Add a table" in suggestion.description
        assert suggestion.widgets == []

    def test_parse_malformed_widget_skipped(self, node: TerminalNode) -> None:
        response = "WIDGETS: bad_widget_def"
        suggestion = node._parse_llm_response("x", response)
        assert len(suggestion.widgets) == 0
