"""Unit tests for Browser Node & Universal Preview.

Tests cover:
- BrowserNode initialization and configuration
- Framework detection (from content, URL, path)
- Element detection from HTML
- Element tagging and untagging
- Natural language editing
- Preview state management
- Tape logging integration
- Framework-specific embed URLs
- Export/serialization

Run with: pytest tests/test_browser_node.py -v
"""

import pytest

from packages.canvas.nodes.browser import (
    BrowserNode,
    BrowserNodeConfig,
    BrowserNodeType,
    DetectedElement,
    ElementDetectionEngine,
    ElementTag,
    ElementTagCategory,
    FrameworkDetector,
    FrameworkType,
    LivePreviewState,
    NaturalLanguageEdit,
    NaturalLanguageEditEngine,
    PreviewMode,
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
def basic_config() -> BrowserNodeConfig:
    return BrowserNodeConfig(
        name="Test Preview",
        node_type=BrowserNodeType.PREVIEW,
        framework=FrameworkType.GENERIC,
        preview_mode=PreviewMode.EMULATED,
    )


@pytest.fixture()
def sample_html() -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <header id="main-header" class="site-header">
            <h1>Welcome</h1>
            <nav class="main-nav">
                <a href="/home">Home</a>
                <a href="/about">About</a>
            </nav>
        </header>
        <main>
            <section class="hero">
                <h2>Hero Section</h2>
                <button class="cta-btn primary" data-action="signup">Sign Up</button>
            </section>
            <form id="contact-form">
                <input type="text" name="name" placeholder="Your name" />
                <button type="submit">Submit</button>
            </form>
        </main>
        <footer>
            <p>Copyright 2024</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture()
def react_html() -> str:
    return '<div id="root" data-reactroot=""><div class="App"><h1>React App</h1></div></div>'


@pytest.fixture()
def vue_html() -> str:
    return '<div id="app" data-v-1234=""><h1>Vue App</h1></div>'


# ---------------------------------------------------------------------------
# FrameworkDetector tests
# ---------------------------------------------------------------------------

class TestFrameworkDetector:
    """Tests for framework detection."""

    def test_detect_react_from_content(self) -> None:
        content = "import React from 'react';\nfunction App() { return <div>Hello</div>; }"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.REACT

    def test_detect_next_js_from_content(self) -> None:
        content = "import { getServerSideProps } from 'next';\nexport default function Page() {}"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.NEXT_JS

    def test_detect_vue_from_content(self) -> None:
        content = "<template>\n  <div>Hello</div>\n</template>\n<script>\nexport default {}\n</script>"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.VUE

    def test_detect_svelte_from_content(self) -> None:
        content = "<script>\n  let count = 0;\n</script>\n<button on:click={() => count++}>"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.SVELTE

    def test_detect_angular_from_content(self) -> None:
        content = "import { Component } from '@angular/core';\n@Component({})"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.ANGULAR

    def test_detect_electron_from_content(self) -> None:
        content = "const { app, BrowserWindow } = require('electron');"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.ELECTRON

    def test_detect_tauri_from_content(self) -> None:
        content = "import { invoke } from '@tauri-apps/api/tauri';"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.TAURI

    def test_detect_generic_when_no_match(self) -> None:
        content = "just some plain text without any framework hints"
        detected = FrameworkDetector.detect_from_content(content)
        assert detected == FrameworkType.GENERIC

    def test_detect_figma_from_url(self) -> None:
        detected = FrameworkDetector.detect_from_url("https://www.figma.com/file/ABC123/MyDesign")
        assert detected == FrameworkType.FIGMA

    def test_detect_next_js_from_url(self) -> None:
        detected = FrameworkDetector.detect_from_url("http://localhost:3000/dashboard")
        assert detected == FrameworkType.NEXT_JS

    def test_detect_vue_from_url(self) -> None:
        detected = FrameworkDetector.detect_from_url("http://localhost:5173/app")
        assert detected == FrameworkType.VUE

    def test_detect_vue_from_path(self) -> None:
        detected = FrameworkDetector.detect_from_path("/project/src/components/App.vue")
        assert detected == FrameworkType.VUE

    def test_detect_svelte_from_path(self) -> None:
        detected = FrameworkDetector.detect_from_path("/project/src/App.svelte")
        assert detected == FrameworkType.SVELTE

    def test_detect_react_from_path(self) -> None:
        detected = FrameworkDetector.detect_from_path("/project/src/App.tsx")
        assert detected == FrameworkType.REACT

    def test_detect_electron_from_path(self) -> None:
        detected = FrameworkDetector.detect_from_path("/project/electron/main.js")
        assert detected == FrameworkType.ELECTRON


# ---------------------------------------------------------------------------
# ElementDetectionEngine tests
# ---------------------------------------------------------------------------

class TestElementDetectionEngine:
    """Tests for element detection from HTML."""

    def test_detect_elements_count(self, sample_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(sample_html)
        # Should detect: header, h1, nav, 2x a, main, section, h2, button, form, input, button, footer, p
        assert len(elements) >= 10

    def test_detect_element_tag_names(self, sample_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(sample_html)
        tag_names = [e.tag_name for e in elements]
        assert "header" in tag_names
        assert "h1" in tag_names
        assert "nav" in tag_names
        assert "a" in tag_names
        assert "button" in tag_names
        assert "form" in tag_names
        assert "input" in tag_names

    def test_detect_element_attributes(self, sample_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(sample_html)
        header = next((e for e in elements if e.tag_name == "header"), None)
        assert header is not None
        assert header.attributes.get("id") == "main-header"
        assert "site-header" in header.attributes.get("class", "")

    def test_detect_element_text_content(self, sample_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(sample_html)
        h1 = next((e for e in elements if e.tag_name == "h1"), None)
        assert h1 is not None
        assert h1.text_content == "Welcome"

    def test_skips_script_and_style(self, sample_html: str) -> None:
        html_with_script = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body>
            <script>console.log('test');</script>
            <div>Content</div>
        </body>
        </html>
        """
        elements = ElementDetectionEngine.detect_elements(html_with_script)
        tag_names = [e.tag_name for e in elements]
        assert "script" not in tag_names
        assert "style" not in tag_names
        assert "div" in tag_names

    def test_detect_react_framework_hint(self, react_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(react_html)
        root = next((e for e in elements if e.tag_name == "div"), None)
        assert root is not None
        assert root.framework_hint == FrameworkType.REACT

    def test_detect_vue_framework_hint(self, vue_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(vue_html)
        app = next((e for e in elements if e.tag_name == "div"), None)
        assert app is not None
        assert app.framework_hint == FrameworkType.VUE

    def test_categorize_element_layout(self) -> None:
        element = DetectedElement(selector="div", tag_name="div")
        category = ElementDetectionEngine.categorize_element(element)
        assert category == ElementTagCategory.LAYOUT

    def test_categorize_element_interactive(self) -> None:
        element = DetectedElement(selector="button", tag_name="button")
        category = ElementDetectionEngine.categorize_element(element)
        assert category == ElementTagCategory.INTERACTIVE

    def test_categorize_element_text(self) -> None:
        element = DetectedElement(selector="h1", tag_name="h1")
        category = ElementDetectionEngine.categorize_element(element)
        assert category == ElementTagCategory.TEXT

    def test_auto_tag_elements(self, sample_html: str) -> None:
        elements = ElementDetectionEngine.detect_elements(sample_html)
        elements = ElementDetectionEngine.auto_tag_elements(elements)
        for element in elements:
            assert len(element.tags) > 0
            assert element.tags[0].name in {
                "layout", "interactive", "media", "form",
                "navigation", "text", "custom",
            }


# ---------------------------------------------------------------------------
# NaturalLanguageEditEngine tests
# ---------------------------------------------------------------------------

class TestNaturalLanguageEditEngine:
    """Tests for natural language editing."""

    def test_parse_color_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make it blue")
        assert result["css_changes"]["color"] == "#3b82f6"
        assert result["action"] == "color_change"

    def test_parse_background_color_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make the background red")
        assert result["css_changes"]["background-color"] == "#ef4444"

    def test_parse_border_color_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make the border green")
        assert result["css_changes"]["border-color"] == "#22c55e"

    def test_parse_font_size_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make the font large")
        assert result["css_changes"]["font-size"] == "1.25rem"
        assert result["action"] == "size_change"

    def test_parse_padding_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("add large padding")
        assert result["css_changes"]["padding"] == "1.25rem"

    def test_parse_text_change(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction('change text to "Hello World"')
        assert result["text_changes"]["content"] == "Hello World"
        assert result["action"] == "text_change"

    def test_parse_rename(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction('rename to "New Button"')
        assert result["text_changes"]["content"] == "New Button"
        assert result["action"] == "text_change"

    def test_parse_hide(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("hide this element")
        assert result["css_changes"]["display"] == "none"
        assert result["action"] == "hide"

    def test_parse_show(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("show this element")
        assert result["css_changes"]["display"] == "block"
        assert result["action"] == "show"

    def test_parse_rounded(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make it rounded")
        assert result["css_changes"]["border-radius"] == "0.5rem"
        assert result["action"] == "style_change"

    def test_parse_bold(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make the text bold")
        assert result["css_changes"]["font-weight"] == "bold"
        assert result["action"] == "style_change"

    def test_parse_italic(self) -> None:
        result = NaturalLanguageEditEngine.parse_instruction("make it italic")
        assert result["css_changes"]["font-style"] == "italic"
        assert result["action"] == "style_change"

    def test_apply_edit(self) -> None:
        edit = NaturalLanguageEdit(instruction="make it blue")
        result = NaturalLanguageEditEngine.apply_edit(edit)
        assert result.status == "applied"
        assert result.applied_changes["css_changes"]["color"] == "#3b82f6"
        assert result.applied_at is not None


# ---------------------------------------------------------------------------
# BrowserNode tests
# ---------------------------------------------------------------------------

class TestBrowserNode:
    """Tests for BrowserNode core functionality."""

    def test_node_initialization(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        assert node.node_id == basic_config.node_id
        assert node.config.name == "Test Preview"
        assert len(node.elements) == 0
        assert len(node.tags) == 0
        assert len(node.edits) == 0

    def test_node_with_tape_service(self, basic_config: BrowserNodeConfig, tape_svc: TapeService) -> None:
        node = BrowserNode(config=basic_config, tape_service=tape_svc)
        assert node._tape is not None

    @pytest.mark.asyncio
    async def test_connect_preview(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        state = await node.connect_preview("http://localhost:3000")
        assert state.is_connected is True
        assert state.url == "http://localhost:3000"
        assert state.error_message is None

    @pytest.mark.asyncio
    async def test_disconnect_preview(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        await node.connect_preview("http://localhost:3000")
        state = await node.disconnect_preview()
        assert state.is_connected is False

    @pytest.mark.asyncio
    async def test_refresh_preview(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        await node.connect_preview("http://localhost:3000")
        state = await node.refresh_preview()
        assert state.last_heartbeat is not None

    @pytest.mark.asyncio
    async def test_load_content(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        elements = await node.load_content(sample_html)
        assert len(elements) > 0
        assert len(node.elements) == len(elements)

    @pytest.mark.asyncio
    async def test_detect_framework_from_content(self, basic_config: BrowserNodeConfig) -> None:
        # detect_from_content works on JS source code, not HTML markup
        react_js = "import React, { useState } from 'react';\nconst App = () => <div />;"
        node = BrowserNode(config=basic_config)
        await node.load_content(react_js)
        assert node.config.framework == FrameworkType.REACT

    def test_get_element_by_id(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        import asyncio
        asyncio.get_event_loop().run_until_complete(node.load_content(sample_html))

        # Get first element and verify lookup works
        first = node.elements[0]
        found = node.get_element_by_id(first.element_id)
        assert found is not None
        assert found.element_id == first.element_id

    def test_get_element_by_id_not_found(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        found = node.get_element_by_id("nonexistent")
        assert found is None

    def test_get_elements_by_tag(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        import asyncio
        asyncio.get_event_loop().run_until_complete(node.load_content(sample_html))

        buttons = node.get_elements_by_tag("button")
        assert len(buttons) >= 2  # CTA + submit

    def test_get_elements_by_selector(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        import asyncio
        asyncio.get_event_loop().run_until_complete(node.load_content(sample_html))

        header_elements = node.get_elements_by_selector("header")
        assert len(header_elements) >= 1

    @pytest.mark.asyncio
    async def test_add_element_tag(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        await node.load_content(sample_html)

        element = node.elements[0]
        tag = ElementTag(name="important", category=ElementTagCategory.CUSTOM, color="#ff0000")

        result = await node.add_element_tag(element.element_id, tag)
        assert result is not None
        assert any(t.name == "important" for t in result.tags)
        assert len(node.tags) == 1

    @pytest.mark.asyncio
    async def test_add_element_tag_not_found(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        tag = ElementTag(name="test")
        result = await node.add_element_tag("nonexistent", tag)
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_element_tag(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        await node.load_content(sample_html)

        element = node.elements[0]
        tag = ElementTag(name="temp")
        await node.add_element_tag(element.element_id, tag)

        result = await node.remove_element_tag(element.element_id, tag.tag_id)
        assert result is not None
        assert not any(t.tag_id == tag.tag_id for t in result.tags)

    @pytest.mark.asyncio
    async def test_apply_natural_language_edit(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        edit = await node.apply_natural_language_edit("make it blue")
        assert edit.status == "applied"
        assert edit.applied_changes["css_changes"]["color"] == "#3b82f6"
        assert len(node.edits) == 1

    @pytest.mark.asyncio
    async def test_apply_nl_edit_with_target(self, basic_config: BrowserNodeConfig, sample_html: str) -> None:
        node = BrowserNode(config=basic_config)
        await node.load_content(sample_html)

        element = node.elements[0]
        edit = await node.apply_natural_language_edit(
            "make it blue",
            target_element_id=element.element_id,
        )
        assert edit.target_element_id == element.element_id
        assert edit.target_selector == element.selector

    def test_get_pending_edits(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            node.apply_natural_language_edit("make it blue")
        )
        pending = node.get_pending_edits()
        assert len(pending) == 0  # Already applied

    def test_get_applied_edits(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            node.apply_natural_language_edit("make it blue")
        )
        applied = node.get_applied_edits()
        assert len(applied) == 1

    def test_get_embed_url_for_figma(self) -> None:
        config = BrowserNodeConfig(
            framework=FrameworkType.FIGMA,
            figma_file_key="ABC123",
            figma_node_id="123:456",
        )
        node = BrowserNode(config=config)
        url = node.get_embed_url()
        assert url is not None
        assert "figma.com/embed" in url
        assert "ABC123" in url
        assert "123:456" in url

    def test_get_embed_url_for_generic(self) -> None:
        config = BrowserNodeConfig(
            framework=FrameworkType.GENERIC,
            source_url="http://localhost:3000",
        )
        node = BrowserNode(config=config)
        url = node.get_embed_url()
        assert url == "http://localhost:3000"

    def test_get_embed_url_for_local_path(self) -> None:
        config = BrowserNodeConfig(
            framework=FrameworkType.ELECTRON,
            source_path="/app/index.html",
        )
        node = BrowserNode(config=config)
        url = node.get_embed_url()
        assert url == "file:///app/index.html"

    def test_get_framework_info_react(self) -> None:
        config = BrowserNodeConfig(framework=FrameworkType.REACT)
        node = BrowserNode(config=config)
        info = node.get_framework_info()
        assert info["name"] == "React"
        assert info["supports_hot_reload"] is True
        assert ".jsx" in info["file_extensions"]

    def test_get_framework_info_electron(self) -> None:
        config = BrowserNodeConfig(framework=FrameworkType.ELECTRON)
        node = BrowserNode(config=config)
        info = node.get_framework_info()
        assert info["name"] == "Electron"
        assert info["supports_hot_reload"] is False

    def test_get_framework_info_figma(self) -> None:
        config = BrowserNodeConfig(framework=FrameworkType.FIGMA)
        node = BrowserNode(config=config)
        info = node.get_framework_info()
        assert info["name"] == "Figma"
        assert info["dev_server_port"] is None

    def test_to_dict(self, basic_config: BrowserNodeConfig) -> None:
        node = BrowserNode(config=basic_config)
        data = node.to_dict()
        assert data["node_id"] == basic_config.node_id
        assert "config" in data
        assert "preview_state" in data
        assert "framework_info" in data
        assert data["element_count"] == 0

    @pytest.mark.asyncio
    async def test_tape_logging(self, basic_config: BrowserNodeConfig, tape_svc: TapeService) -> None:
        node = BrowserNode(config=basic_config, tape_service=tape_svc)
        await node.connect_preview("http://localhost:3000")

        entries = await tape_svc.get_entries(event_type="canvas.browser_preview_connected")
        assert len(entries) == 1
        assert entries[0].payload["node_id"] == node.node_id

    @pytest.mark.asyncio
    async def test_tape_logging_content_load(self, basic_config: BrowserNodeConfig, tape_svc: TapeService, sample_html: str) -> None:
        node = BrowserNode(config=basic_config, tape_service=tape_svc)
        await node.load_content(sample_html)

        entries = await tape_svc.get_entries(event_type="canvas.browser_content_loaded")
        assert len(entries) == 1
        element_count = entries[0].payload["element_count"]
        assert isinstance(element_count, int) and element_count > 0

    @pytest.mark.asyncio
    async def test_tape_logging_element_tag(self, basic_config: BrowserNodeConfig, tape_svc: TapeService, sample_html: str) -> None:
        node = BrowserNode(config=basic_config, tape_service=tape_svc)
        await node.load_content(sample_html)

        element = node.elements[0]
        tag = ElementTag(name="test-tag")
        await node.add_element_tag(element.element_id, tag)

        entries = await tape_svc.get_entries(event_type="canvas.browser_element_tagged")
        assert len(entries) == 1
        assert entries[0].payload["tag_name"] == "test-tag"

    @pytest.mark.asyncio
    async def test_tape_logging_nl_edit(self, basic_config: BrowserNodeConfig, tape_svc: TapeService) -> None:
        node = BrowserNode(config=basic_config, tape_service=tape_svc)
        await node.apply_natural_language_edit("make it blue")

        entries = await tape_svc.get_entries(event_type="canvas.browser_nl_edit_applied")
        assert len(entries) == 1
        assert entries[0].payload["instruction"] == "make it blue"


# ---------------------------------------------------------------------------
# DetectedElement tests
# ---------------------------------------------------------------------------

class TestDetectedElement:
    """Tests for DetectedElement model."""

    def test_add_tag(self) -> None:
        element = DetectedElement(selector="div", tag_name="div")
        tag1 = ElementTag(name="layout")
        tag2 = ElementTag(name="important")

        element.add_tag(tag1)
        element.add_tag(tag2)
        assert len(element.tags) == 2

    def test_add_duplicate_tag_ignored(self) -> None:
        element = DetectedElement(selector="div", tag_name="div")
        tag = ElementTag(name="layout")
        element.add_tag(tag)
        element.add_tag(tag)
        assert len(element.tags) == 1

    def test_remove_tag(self) -> None:
        element = DetectedElement(selector="div", tag_name="div")
        tag = ElementTag(name="layout")
        element.add_tag(tag)
        element.remove_tag(tag.tag_id)
        assert len(element.tags) == 0


# ---------------------------------------------------------------------------
# ElementTag tests
# ---------------------------------------------------------------------------

class TestElementTag:
    """Tests for ElementTag model."""

    def test_default_values(self) -> None:
        tag = ElementTag(name="test")
        assert tag.name == "test"
        assert tag.category == ElementTagCategory.CUSTOM
        assert tag.color == "#3b82f6"
        assert tag.description == ""

    def test_custom_values(self) -> None:
        tag = ElementTag(
            name="layout",
            category=ElementTagCategory.LAYOUT,
            color="#8b5cf6",
            description="Layout element",
        )
        assert tag.category == ElementTagCategory.LAYOUT
        assert tag.color == "#8b5cf6"


# ---------------------------------------------------------------------------
# BrowserNodeConfig tests
# ---------------------------------------------------------------------------

class TestBrowserNodeConfig:
    """Tests for BrowserNodeConfig model."""

    def test_default_config(self) -> None:
        config = BrowserNodeConfig()
        assert config.name == "Browser Preview"
        assert config.node_type == BrowserNodeType.PREVIEW
        assert config.framework == FrameworkType.GENERIC
        assert config.preview_mode == PreviewMode.EMULATED
        assert config.width == 1280
        assert config.height == 720

    def test_custom_config(self) -> None:
        config = BrowserNodeConfig(
            name="My App",
            node_type=BrowserNodeType.COMPONENT,
            framework=FrameworkType.REACT,
            preview_mode=PreviewMode.LIVE,
            width=1920,
            height=1080,
        )
        assert config.name == "My App"
        assert config.framework == FrameworkType.REACT
        assert config.width == 1920


# ---------------------------------------------------------------------------
# LivePreviewState tests
# ---------------------------------------------------------------------------

class TestLivePreviewState:
    """Tests for LivePreviewState model."""

    def test_default_state(self) -> None:
        state = LivePreviewState()
        assert state.is_connected is False
        assert state.framework == FrameworkType.GENERIC
        assert state.preview_mode == PreviewMode.EMULATED

    def test_connected_state(self) -> None:
        from packages.canvas.nodes.browser import LivePreviewState
        state = LivePreviewState(
            url="http://localhost:3000",
            is_connected=True,
            framework=FrameworkType.REACT,
        )
        assert state.is_connected is True
        assert state.url == "http://localhost:3000"
