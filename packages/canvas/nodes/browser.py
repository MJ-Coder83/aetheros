"""Browser Node & Universal Preview for the Domain Canvas.

Provides live embedding support for web frameworks (React, Next.js, Vue, etc.),
Electron, Tauri, Figma, and basic emulation for others. Includes element
detection, tagging, and natural language editing support.

All operations are logged to the Tape for full auditability.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BrowserNodeType(StrEnum):
    """Type of browser node in the canvas."""

    PREVIEW = "preview"
    COMPONENT = "component"
    PAGE = "page"
    IFRAME = "iframe"
    WIDGET = "widget"


class FrameworkType(StrEnum):
    """Supported web/framework types for live embedding."""

    REACT = "react"
    NEXT_JS = "next_js"
    VUE = "vue"
    SVELTE = "svelte"
    ANGULAR = "angular"
    ELECTRON = "electron"
    TAURI = "tauri"
    FIGMA = "figma"
    HTML = "html"
    GENERIC = "generic"


class PreviewMode(StrEnum):
    """How the preview is rendered."""

    LIVE = "live"
    STATIC = "static"
    EMULATED = "emulated"
    SNAPSHOT = "snapshot"


class ElementTagCategory(StrEnum):
    """Category for element tags."""

    LAYOUT = "layout"
    INTERACTIVE = "interactive"
    MEDIA = "media"
    FORM = "form"
    NAVIGATION = "navigation"
    TEXT = "text"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ElementTag(BaseModel):
    """A tag attached to a detected element for organization and filtering."""

    tag_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: ElementTagCategory = ElementTagCategory.CUSTOM
    color: str = "#3b82f6"  # Default blue
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DetectedElement(BaseModel):
    """An element detected within a browser preview for interaction/editing."""

    element_id: str = Field(default_factory=lambda: str(uuid4()))
    selector: str  # CSS selector or XPath
    tag_name: str  # e.g. "div", "button", "img"
    text_content: str = ""
    attributes: dict[str, str] = Field(default_factory=dict)
    bounding_box: dict[str, float] = Field(default_factory=dict)  # x, y, width, height
    tags: list[ElementTag] = Field(default_factory=list)
    is_editable: bool = True
    framework_hint: FrameworkType | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_tag(self, tag: ElementTag) -> None:
        """Add a tag to this element if not already present."""
        if not any(t.tag_id == tag.tag_id for t in self.tags):
            self.tags.append(tag)

    def remove_tag(self, tag_id: str) -> None:
        """Remove a tag by ID."""
        self.tags = [t for t in self.tags if t.tag_id != tag_id]


class NaturalLanguageEdit(BaseModel):
    """A natural language instruction for editing an element or component."""

    edit_id: str = Field(default_factory=lambda: str(uuid4()))
    instruction: str  # e.g. "Make the button blue and larger"
    target_element_id: str | None = None
    target_selector: str | None = None
    applied_changes: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, applied, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    applied_at: datetime | None = None


class LivePreviewState(BaseModel):
    """Current state of a live preview session."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    url: str | None = None
    port: int | None = None
    is_connected: bool = False
    last_heartbeat: datetime | None = None
    framework: FrameworkType = FrameworkType.GENERIC
    preview_mode: PreviewMode = PreviewMode.EMULATED
    error_message: str | None = None


class BrowserNodeConfig(BaseModel):
    """Configuration for a BrowserNode."""

    node_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = "Browser Preview"
    node_type: BrowserNodeType = BrowserNodeType.PREVIEW
    framework: FrameworkType = FrameworkType.GENERIC
    preview_mode: PreviewMode = PreviewMode.EMULATED
    source_url: str | None = None
    source_path: str | None = None  # Local file path for Electron/Tauri
    figma_file_key: str | None = None
    figma_node_id: str | None = None
    width: int = 1280
    height: int = 720
    auto_refresh: bool = False
    refresh_interval_ms: int = 5000
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------


class FrameworkDetector:
    """Detects the framework type from source code, URLs, or file paths."""

    _PATTERNS: ClassVar[dict[FrameworkType, list[str]]] = {
        FrameworkType.REACT: [
            r"import\s+React",
            r"from\s+['\"]react['\"]",
            r"React\.createElement",
            r"\.jsx?$",
            r"\.tsx?$",
        ],
        FrameworkType.NEXT_JS: [
            r"from\s+['\"]next",
            r"getServerSideProps",
            r"getStaticProps",
            r"app/\(routing\)",
            r"next\.config",
        ],
        FrameworkType.VUE: [
            r"<template>",
            r"\.vue$",
            r"createApp",
            r"from\s+['\"]vue['\"]",
        ],
        FrameworkType.SVELTE: [
            r"\.svelte$",
            r"<script\s+lang=",
            r"on:click",
            r"bind:",
        ],
        FrameworkType.ANGULAR: [
            r"@Component",
            r"\.component\.ts$",
            r"@angular",
        ],
        FrameworkType.ELECTRON: [
            r"electron",
            r"main\.js",
            r"preload\.js",
            r"BrowserWindow",
        ],
        FrameworkType.TAURI: [
            r"tauri",
            r"tauri\.conf",
            r"invoke\s*\(",
        ],
        FrameworkType.FIGMA: [
            r"figma\.com",
            r"figma\.com/file/",
        ],
    }

    @classmethod
    def detect_from_content(cls, content: str) -> FrameworkType:
        """Detect framework from source code content."""
        scores: dict[FrameworkType, int] = {}
        for framework, patterns in cls._PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, content, re.IGNORECASE))
            if score > 0:
                scores[framework] = score
        if not scores:
            return FrameworkType.GENERIC
        return max(scores, key=lambda k: scores[k])

    @classmethod
    def detect_from_url(cls, url: str) -> FrameworkType:
        """Detect framework from a URL."""
        url_lower = url.lower()
        if "figma.com" in url_lower:
            return FrameworkType.FIGMA
        if "localhost:3000" in url_lower:
            return FrameworkType.NEXT_JS
        if "localhost:5173" in url_lower or "localhost:8080" in url_lower:
            return FrameworkType.VUE
        if "localhost:4321" in url_lower:
            return FrameworkType.SVELTE
        return FrameworkType.GENERIC

    @classmethod
    def detect_from_path(cls, path: str) -> FrameworkType:
        """Detect framework from a file path."""
        path_lower = path.lower()
        if path_lower.endswith(".vue"):
            return FrameworkType.VUE
        if path_lower.endswith(".svelte"):
            return FrameworkType.SVELTE
        if ".tsx" in path_lower or ".jsx" in path_lower:
            return FrameworkType.REACT
        if "electron" in path_lower:
            return FrameworkType.ELECTRON
        if "tauri" in path_lower:
            return FrameworkType.TAURI
        return FrameworkType.GENERIC


# ---------------------------------------------------------------------------
# Element detection engine
# ---------------------------------------------------------------------------


class ElementDetectionEngine:
    """Detects and extracts elements from HTML/content for canvas interaction."""

    _INTERACTIVE_TAGS: ClassVar[set[str]] = {
        "button",
        "a",
        "input",
        "select",
        "textarea",
        "form",
        "label",
        "option",
        "details",
        "summary",
    }
    _MEDIA_TAGS: ClassVar[set[str]] = {
        "img",
        "video",
        "audio",
        "canvas",
        "svg",
        "iframe",
    }
    _LAYOUT_TAGS: ClassVar[set[str]] = {
        "div",
        "section",
        "article",
        "aside",
        "header",
        "footer",
        "nav",
        "main",
        "figure",
        "figcaption",
    }
    _TEXT_TAGS: ClassVar[set[str]] = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "span",
        "strong",
        "em",
        "blockquote",
        "code",
        "pre",
    }
    _NAV_TAGS: ClassVar[set[str]] = {
        "nav",
        "a",
        "menu",
        "ol",
        "ul",
        "li",
    }

    @classmethod
    def detect_elements(cls, html_content: str) -> list[DetectedElement]:
        """Detect interactive elements from HTML content.

        Uses a lightweight regex-based parser suitable for canvas previews.
        For production, this would use a proper HTML parser like BeautifulSoup.
        """
        elements: list[DetectedElement] = []

        # Match opening tags with attributes
        tag_pattern = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>([^<]*)")

        for match in tag_pattern.finditer(html_content):
            tag_name = match.group(1).lower()
            attrs_str = match.group(2)
            text_content = match.group(3).strip()

            # Skip script/style tags
            if tag_name in {"script", "style", "meta", "link", "br", "hr"}:
                continue

            # Parse attributes (handle hyphens in attribute names)
            attributes: dict[str, str] = {}
            attr_pattern = re.compile(r'([\w-]+)(?:=["\']([^"\']*)["\'])?')
            for attr_match in attr_pattern.finditer(attrs_str):
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2) or ""
                if attr_name:  # Skip empty matches
                    attributes[attr_name] = attr_value

            # Build selector
            selector = tag_name
            if "id" in attributes:
                selector = f"#{attributes['id']}"
            elif "class" in attributes:
                classes = attributes["class"].split()[:2]  # First 2 classes
                selector = f"{tag_name}.{'.'.join(classes)}"

            # Determine if editable
            is_editable = tag_name in cls._INTERACTIVE_TAGS or "contenteditable" in attributes

            # Determine framework hint
            framework_hint = None
            if any(k.startswith("data-react") for k in attributes):
                framework_hint = FrameworkType.REACT
            elif any(k.startswith("data-v-") for k in attributes):
                framework_hint = FrameworkType.VUE

            element = DetectedElement(
                selector=selector,
                tag_name=tag_name,
                text_content=text_content,
                attributes=attributes,
                is_editable=is_editable,
                framework_hint=framework_hint,
            )
            elements.append(element)

        return elements

    @classmethod
    def categorize_element(cls, element: DetectedElement) -> ElementTagCategory:
        """Categorize an element by its tag name."""
        tag = element.tag_name.lower()
        if tag in cls._INTERACTIVE_TAGS:
            return ElementTagCategory.INTERACTIVE
        if tag in cls._MEDIA_TAGS:
            return ElementTagCategory.MEDIA
        if tag in cls._LAYOUT_TAGS:
            return ElementTagCategory.LAYOUT
        if tag in cls._TEXT_TAGS:
            return ElementTagCategory.TEXT
        if tag in cls._NAV_TAGS:
            return ElementTagCategory.NAVIGATION
        return ElementTagCategory.CUSTOM

    @classmethod
    def auto_tag_elements(cls, elements: list[DetectedElement]) -> list[DetectedElement]:
        """Automatically assign category tags to detected elements."""
        for element in elements:
            category = cls.categorize_element(element)
            tag = ElementTag(
                name=category.value,
                category=category,
                color=cls._tag_color_for_category(category),
            )
            element.add_tag(tag)
        return elements

    @classmethod
    def _tag_color_for_category(cls, category: ElementTagCategory) -> str:
        colors = {
            ElementTagCategory.LAYOUT: "#8b5cf6",  # violet
            ElementTagCategory.INTERACTIVE: "#3b82f6",  # blue
            ElementTagCategory.MEDIA: "#ec4899",  # pink
            ElementTagCategory.FORM: "#10b981",  # emerald
            ElementTagCategory.NAVIGATION: "#f59e0b",  # amber
            ElementTagCategory.TEXT: "#6b7280",  # gray
            ElementTagCategory.CUSTOM: "#6366f1",  # indigo
        }
        return colors.get(category, "#6366f1")


# ---------------------------------------------------------------------------
# Natural language editing engine
# ---------------------------------------------------------------------------


class NaturalLanguageEditEngine:
    """Processes natural language editing instructions for browser nodes.

    Parses instructions like "make the button blue" or "add padding to the header"
    and converts them to structured CSS/property changes.
    """

    _COLOR_MAP: ClassVar[dict[str, str]] = {
        "red": "#ef4444",
        "blue": "#3b82f6",
        "green": "#22c55e",
        "yellow": "#eab308",
        "purple": "#a855f7",
        "orange": "#f97316",
        "pink": "#ec4899",
        "gray": "#6b7280",
        "black": "#000000",
        "white": "#ffffff",
    }

    _SIZE_MAP: ClassVar[dict[str, str]] = {
        "small": "0.75rem",
        "smaller": "0.625rem",
        "normal": "1rem",
        "medium": "1rem",
        "large": "1.25rem",
        "larger": "1.5rem",
        "big": "1.5rem",
        "huge": "2rem",
    }

    @classmethod
    def parse_instruction(cls, instruction: str) -> dict[str, Any]:
        """Parse a natural language instruction into structured changes.

        Returns a dict with keys like 'css_changes', 'text_changes', 'action'.
        """
        instruction_lower = instruction.lower().strip()
        result: dict[str, Any] = {"action": None, "css_changes": {}, "text_changes": {}}

        # Color changes
        for color_name, hex_code in cls._COLOR_MAP.items():
            if f" {color_name}" in instruction_lower or instruction_lower.startswith(color_name):
                if "background" in instruction_lower or "bg " in instruction_lower:
                    result["css_changes"]["background-color"] = hex_code
                elif "border" in instruction_lower:
                    result["css_changes"]["border-color"] = hex_code
                else:
                    result["css_changes"]["color"] = hex_code
                result["action"] = "color_change"

        # Size changes
        for size_name, size_value in cls._SIZE_MAP.items():
            if f" {size_name}" in instruction_lower:
                if "font" in instruction_lower or "text" in instruction_lower:
                    result["css_changes"]["font-size"] = size_value
                elif "padding" in instruction_lower:
                    result["css_changes"]["padding"] = size_value
                elif "margin" in instruction_lower:
                    result["css_changes"]["margin"] = size_value
                else:
                    result["css_changes"]["width"] = size_value
                result["action"] = "size_change"

        # Text content changes
        if "change text to" in instruction_lower:
            match = re.search(r'change text to ["\']([^"\']+)["\']', instruction, re.IGNORECASE)
            if match:
                result["text_changes"]["content"] = match.group(1)
                result["action"] = "text_change"

        if "rename to" in instruction_lower:
            match = re.search(r'rename to ["\']([^"\']+)["\']', instruction, re.IGNORECASE)
            if match:
                result["text_changes"]["content"] = match.group(1)
                result["action"] = "text_change"

        # Visibility
        if "hide" in instruction_lower:
            result["css_changes"]["display"] = "none"
            result["action"] = "hide"
        elif "show" in instruction_lower:
            result["css_changes"]["display"] = "block"
            result["action"] = "show"

        # Border radius
        if "rounded" in instruction_lower or "round" in instruction_lower:
            result["css_changes"]["border-radius"] = "0.5rem"
            result["action"] = "style_change"

        # Bold/italic
        if "bold" in instruction_lower:
            result["css_changes"]["font-weight"] = "bold"
            result["action"] = "style_change"
        if "italic" in instruction_lower:
            result["css_changes"]["font-style"] = "italic"
            result["action"] = "style_change"

        return result

    @classmethod
    def apply_edit(
        cls,
        edit: NaturalLanguageEdit,
        element: DetectedElement | None = None,
    ) -> NaturalLanguageEdit:
        """Apply a natural language edit to an element or return the parsed result."""
        parsed = cls.parse_instruction(edit.instruction)

        edit.applied_changes = parsed
        edit.status = "applied"
        edit.applied_at = datetime.now(UTC)

        return edit


# ---------------------------------------------------------------------------
# Browser Node
# ---------------------------------------------------------------------------


class BrowserNode:
    """A canvas node that renders live browser previews for web frameworks.

    Supports:
    - Live embedding for React, Next.js, Vue, Svelte, Angular
    - Electron and Tauri app previews
    - Figma design embeds
    - Basic emulation for unsupported frameworks
    - Element detection and tagging
    - Natural language editing

    All operations are logged to the Tape for auditability.
    """

    def __init__(
        self,
        config: BrowserNodeConfig,
        tape_service: TapeService | None = None,
    ) -> None:
        self.config = config
        self._tape = tape_service
        self._elements: list[DetectedElement] = []
        self._tags: dict[str, ElementTag] = {}
        self._edits: list[NaturalLanguageEdit] = []
        self._preview_state = LivePreviewState(
            framework=config.framework,
            preview_mode=config.preview_mode,
        )
        self._content_cache: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_id(self) -> str:
        return self.config.node_id

    @property
    def elements(self) -> list[DetectedElement]:
        return list(self._elements)

    @property
    def tags(self) -> list[ElementTag]:
        return list(self._tags.values())

    @property
    def edits(self) -> list[NaturalLanguageEdit]:
        return list(self._edits)

    @property
    def preview_state(self) -> LivePreviewState:
        return self._preview_state

    # ------------------------------------------------------------------
    # Framework detection
    # ------------------------------------------------------------------

    def detect_framework(self, content: str | None = None) -> FrameworkType:
        """Auto-detect the framework from available sources."""
        detected = self.config.framework

        if content is not None:
            detected = FrameworkDetector.detect_from_content(content)
            # Fallback: check for framework hints in HTML attributes
            if detected == FrameworkType.GENERIC:
                if "data-react" in content or "data-reactroot" in content:
                    detected = FrameworkType.REACT
                elif "data-v-" in content:
                    detected = FrameworkType.VUE
                elif "on:click" in content or "bind:" in content:
                    detected = FrameworkType.SVELTE

        elif self.config.source_url:
            detected = FrameworkDetector.detect_from_url(self.config.source_url)
        elif self.config.source_path:
            detected = FrameworkDetector.detect_from_path(self.config.source_path)

        self.config.framework = detected
        self._preview_state.framework = detected
        return detected

    # ------------------------------------------------------------------
    # Preview management
    # ------------------------------------------------------------------

    async def connect_preview(self, url: str | None = None) -> LivePreviewState:
        """Connect to a live preview (emulated for now)."""
        if url:
            self.config.source_url = url
            self._preview_state.url = url

        self._preview_state.is_connected = True
        self._preview_state.last_heartbeat = datetime.now(UTC)
        self._preview_state.error_message = None

        # Auto-detect framework from URL
        if self.config.source_url:
            self.detect_framework()

        await self._log_event(
            "canvas.browser_preview_connected",
            {
                "node_id": self.node_id,
                "url": self.config.source_url,
                "framework": self.config.framework.value,
                "preview_mode": self.config.preview_mode.value,
            },
        )
        return self._preview_state

    async def disconnect_preview(self) -> LivePreviewState:
        """Disconnect the live preview."""
        self._preview_state.is_connected = False
        self._preview_state.last_heartbeat = None

        await self._log_event(
            "canvas.browser_preview_disconnected",
            {"node_id": self.node_id},
        )
        return self._preview_state

    async def refresh_preview(self) -> LivePreviewState:
        """Refresh the preview content."""
        self._preview_state.last_heartbeat = datetime.now(UTC)

        await self._log_event(
            "canvas.browser_preview_refreshed",
            {"node_id": self.node_id, "url": self.config.source_url},
        )
        return self._preview_state

    # ------------------------------------------------------------------
    # Content loading
    # ------------------------------------------------------------------

    async def load_content(self, content: str) -> list[DetectedElement]:
        """Load HTML/content and detect elements."""
        self._content_cache = content
        self.detect_framework(content)

        # Detect elements
        self._elements = ElementDetectionEngine.detect_elements(content)
        self._elements = ElementDetectionEngine.auto_tag_elements(self._elements)

        await self._log_event(
            "canvas.browser_content_loaded",
            {
                "node_id": self.node_id,
                "framework": self.config.framework.value,
                "element_count": len(self._elements),
                "content_length": len(content),
            },
        )
        return self._elements

    # ------------------------------------------------------------------
    # Element operations
    # ------------------------------------------------------------------

    def get_element_by_id(self, element_id: str) -> DetectedElement | None:
        """Find an element by its ID."""
        for element in self._elements:
            if element.element_id == element_id:
                return element
        return None

    def get_elements_by_tag(self, tag_name: str) -> list[DetectedElement]:
        """Find elements by tag name."""
        return [e for e in self._elements if e.tag_name == tag_name.lower()]

    def get_elements_by_selector(self, selector: str) -> list[DetectedElement]:
        """Find elements matching a CSS selector (simple substring match)."""
        return [e for e in self._elements if selector in e.selector]

    async def add_element_tag(
        self,
        element_id: str,
        tag: ElementTag,
    ) -> DetectedElement | None:
        """Add a tag to an element."""
        element = self.get_element_by_id(element_id)
        if element is None:
            return None

        element.add_tag(tag)
        self._tags[tag.tag_id] = tag

        await self._log_event(
            "canvas.browser_element_tagged",
            {
                "node_id": self.node_id,
                "element_id": element_id,
                "tag_name": tag.name,
                "tag_category": tag.category.value,
            },
        )
        return element

    async def remove_element_tag(
        self,
        element_id: str,
        tag_id: str,
    ) -> DetectedElement | None:
        """Remove a tag from an element."""
        element = self.get_element_by_id(element_id)
        if element is None:
            return None

        element.remove_tag(tag_id)

        await self._log_event(
            "canvas.browser_element_untagged",
            {
                "node_id": self.node_id,
                "element_id": element_id,
                "tag_id": tag_id,
            },
        )
        return element

    # ------------------------------------------------------------------
    # Natural language editing
    # ------------------------------------------------------------------

    async def apply_natural_language_edit(
        self,
        instruction: str,
        target_element_id: str | None = None,
    ) -> NaturalLanguageEdit:
        """Apply a natural language editing instruction.

        Args:
            instruction: Natural language instruction (e.g. "make it blue").
            target_element_id: Optional specific element to target.

        Returns:
            The NaturalLanguageEdit record with applied changes.
        """
        edit = NaturalLanguageEdit(
            instruction=instruction,
            target_element_id=target_element_id,
        )

        target_element = None
        if target_element_id:
            target_element = self.get_element_by_id(target_element_id)
            if target_element:
                edit.target_selector = target_element.selector

        edit = NaturalLanguageEditEngine.apply_edit(edit, target_element)
        self._edits.append(edit)

        await self._log_event(
            "canvas.browser_nl_edit_applied",
            {
                "node_id": self.node_id,
                "edit_id": edit.edit_id,
                "instruction": instruction,
                "target_element_id": target_element_id,
                "changes": edit.applied_changes,
                "status": edit.status,
            },
        )
        return edit

    def get_pending_edits(self) -> list[NaturalLanguageEdit]:
        """Return all pending natural language edits."""
        return [e for e in self._edits if e.status == "pending"]

    def get_applied_edits(self) -> list[NaturalLanguageEdit]:
        """Return all applied natural language edits."""
        return [e for e in self._edits if e.status == "applied"]

    # ------------------------------------------------------------------
    # Framework-specific helpers
    # ------------------------------------------------------------------

    def get_embed_url(self) -> str | None:
        """Get the embed URL for the current framework."""
        if self.config.framework == FrameworkType.FIGMA:
            if self.config.figma_file_key:
                url = f"https://www.figma.com/embed?embed_host=canvas&url=https://www.figma.com/file/{self.config.figma_file_key}"
                if self.config.figma_node_id:
                    url += f"?node-id={self.config.figma_node_id}"
                return url
            return None

        if self.config.source_url:
            return self.config.source_url

        if self.config.source_path:
            # For Electron/Tauri, return a local preview path
            return f"file://{self.config.source_path}"

        return None

    def get_framework_info(self) -> dict[str, Any]:
        """Get information about the detected framework."""
        info = {
            FrameworkType.REACT: {
                "name": "React",
                "supports_hot_reload": True,
                "dev_server_port": 3000,
                "file_extensions": [".jsx", ".tsx"],
            },
            FrameworkType.NEXT_JS: {
                "name": "Next.js",
                "supports_hot_reload": True,
                "dev_server_port": 3000,
                "file_extensions": [".tsx", ".jsx"],
            },
            FrameworkType.VUE: {
                "name": "Vue",
                "supports_hot_reload": True,
                "dev_server_port": 5173,
                "file_extensions": [".vue"],
            },
            FrameworkType.SVELTE: {
                "name": "Svelte",
                "supports_hot_reload": True,
                "dev_server_port": 5173,
                "file_extensions": [".svelte"],
            },
            FrameworkType.ANGULAR: {
                "name": "Angular",
                "supports_hot_reload": True,
                "dev_server_port": 4200,
                "file_extensions": [".ts", ".html"],
            },
            FrameworkType.ELECTRON: {
                "name": "Electron",
                "supports_hot_reload": False,
                "dev_server_port": None,
                "file_extensions": [".js", ".ts", ".html"],
            },
            FrameworkType.TAURI: {
                "name": "Tauri",
                "supports_hot_reload": True,
                "dev_server_port": 1420,
                "file_extensions": [".rs", ".tsx", ".vue"],
            },
            FrameworkType.FIGMA: {
                "name": "Figma",
                "supports_hot_reload": False,
                "dev_server_port": None,
                "file_extensions": [],
            },
            FrameworkType.HTML: {
                "name": "HTML",
                "supports_hot_reload": True,
                "dev_server_port": 8080,
                "file_extensions": [".html"],
            },
            FrameworkType.GENERIC: {
                "name": "Generic",
                "supports_hot_reload": False,
                "dev_server_port": None,
                "file_extensions": [],
            },
        }
        return info.get(self.config.framework, info[FrameworkType.GENERIC])

    # ------------------------------------------------------------------
    # Export / serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the browser node to a dictionary."""
        return {
            "node_id": self.node_id,
            "config": self.config.model_dump(),
            "preview_state": self._preview_state.model_dump(),
            "element_count": len(self._elements),
            "tag_count": len(self._tags),
            "edit_count": len(self._edits),
            "framework_info": self.get_framework_info(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log an event to the Tape if a tape service is configured."""
        if self._tape is not None:
            await self._tape.log_event(
                event_type=event_type,
                payload=payload,
                agent_id="browser-node",
            )
