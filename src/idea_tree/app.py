"""Centered minimalist Textual shell for idea taxonomies."""

from __future__ import annotations

import os
import re
import webbrowser
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, Static

from .brain import Brain, BrainError
from .tree import ClarifyResult, TreeResult, to_html, to_markdown


def _save_dir() -> Path:
    raw = os.environ.get("IDEA_TREE_SAVE_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "idea-trees"


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "-", s).strip("-").lower()
    return s[:48] or "idea"


class IdeaTreeApp(App[None]):
    """A quiet centered surface for taxonomifying ideas."""

    TITLE = "idea-tree"
    CSS = """
    Screen {
        background: #0c0c0b;
        color: #e8e4d9;
        align: center top;
        layout: vertical;
    }

    #stage {
        width: 84;
        max-width: 94%;
        height: 1fr;
        layout: vertical;
        padding: 1 2 0 2;
    }

    #mode-line {
        width: 100%;
        color: #5a5650;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }

    #user-line {
        width: 100%;
        color: #8a8680;
        text-align: center;
        text-style: italic;
        height: auto;
        min-height: 1;
        max-height: 3;
        margin-bottom: 1;
    }

    #prompt {
        width: 100%;
        background: #0c0c0b;
        color: #f2efe6;
        border: none;
        border-bottom: solid #3a3834;
        padding: 0 1;
        text-align: center;
        height: 3;
    }

    #prompt:focus {
        border-bottom: solid #6b6560;
    }

    #divider {
        width: 100%;
        color: #2e2c28;
        text-align: center;
        height: 1;
        margin: 1 0;
    }

    #tree-scroll {
        width: 100%;
        height: 1fr;
        min-height: 6;
        background: #0c0c0b;
        scrollbar-color: #3a3834;
        scrollbar-background: #0c0c0b;
    }

    #tree {
        width: 100%;
        height: auto;
        color: #c9c2b0;
        text-align: left;
        min-height: 2;
        padding: 0 2;
    }

    #tree.-clarify {
        color: #a8a090;
        text-align: center;
        text-style: italic;
    }

    #tree.-error {
        color: #b07070;
        text-align: center;
        text-style: none;
    }

    #footer {
        dock: bottom;
        width: 100%;
        height: auto;
        min-height: 2;
        background: #0c0c0b;
        padding: 0 2 1 2;
    }

    #status {
        width: 100%;
        color: #6b6560;
        text-align: center;
        height: auto;
        min-height: 1;
        max-height: 3;
    }

    #status.-ok {
        color: #9aaf88;
    }

    #status.-err {
        color: #b07070;
    }

    #hint {
        width: 100%;
        color: #7a746c;
        text-align: center;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "quit", "Quit", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False),
        # priority=True: fire while the Input is focused
        Binding("ctrl+l", "clear", "Clear", show=False, priority=True),
        Binding("ctrl+s", "save", "Save", show=False, priority=True),
        Binding("ctrl+e", "export_html", "HTML", show=False, priority=True),
        # ctrl+m is Enter in terminals (CR) — use ctrl+t for mode / ctrl+p for provider
        Binding("ctrl+t", "cycle_mode", "Mode", show=False, priority=True),
        Binding("ctrl+p", "cycle_provider", "Provider", show=False, priority=True),
    ]

    def __init__(self, brain: Brain) -> None:
        super().__init__()
        self.brain = brain
        self._busy = False
        self._last_save_path: Path | None = None
        self._title_line = ""
        self._status_timer = None

    def compose(self) -> ComposeResult:
        with Vertical(id="stage"):
            yield Static("", id="mode-line", markup=False)
            yield Static("", id="user-line", markup=False)
            yield Input(
                placeholder="name a thing, domain, or half-formed idea…",
                id="prompt",
            )
            yield Static("·  ·  ·", id="divider", markup=False)
            with VerticalScroll(id="tree-scroll"):
                # markup=False: tree labels use [Name] brackets; Rich would eat them
                yield Static("", id="tree", markup=False)
        with Vertical(id="footer"):
            yield Static("", id="status", markup=False)
            yield Static(
                "enter · ctrl+t mode · ctrl+p provider · ctrl+s save · ctrl+e export · ctrl+l clear · esc quit",
                id="hint",
                markup=False,
            )

    def on_mount(self) -> None:
        self._refresh_mode_line()
        self.query_one("#prompt", Input).focus()

    def _refresh_mode_line(self, *, suffix: str | None = None) -> None:
        """Show depth mode; optional status suffix (thinking / tree title / etc.)."""
        base = f"{self.brain.provider_label} · {self.brain.mode_label}"
        if suffix:
            line = f"{base} · {suffix}"
        elif self._title_line:
            line = f"{base} · {self._title_line}"
        else:
            line = f"{base} · taxonomify"
        self.query_one("#mode-line", Static).update(line)

    def action_cycle_provider(self) -> None:
        if self._busy:
            return
        key = self.brain.cycle_provider(clear_history=True)
        if not key:
            self._set_status(
                "no other API key found — set OPENAI_API_KEY or XAI_API_KEY",
                kind="err", hold=6.0,
            )
            return
        label = self.brain.provider_label
        self._title_line = ""
        self._refresh_mode_line()
        self._set_status(
            f"provider → {label} (history cleared) · re-enter idea to regrow",
            hold=5.0,
        )
        tree = self.query_one("#tree", Static)
        if not self.brain.last_display:
            tree.update(f"provider: {label}")
        self.query_one("#prompt", Input).focus()

    def action_cycle_mode(self) -> None:
        if self._busy:
            return
        key = self.brain.cycle_mode(clear_history=True)
        label = self.brain.mode_label
        self._title_line = ""
        self._refresh_mode_line()
        self._set_status(
            f"mode → {label} (history cleared) · re-enter idea to regrow",
            hold=5.0,
        )
        # Soft signal in tree area if empty
        tree = self.query_one("#tree", Static)
        if not self.brain.last_display:
            tree.update(f"mode: {label}")
        self.query_one("#prompt", Input).focus()
        _ = key

    def _set_tree_classes(self, *names: str) -> None:
        tree = self.query_one("#tree", Static)
        tree.remove_class("-clarify", "-error")
        for name in names:
            tree.add_class(name)

    @on(Input.Submitted, "#prompt")
    def on_submit(self, event: Input.Submitted) -> None:
        text = (event.value or "").strip()
        if not text or self._busy:
            return
        event.input.value = ""
        event.input.disabled = True
        self._busy = True
        self.query_one("#user-line", Static).update(text)
        self._set_status("")
        tree = self.query_one("#tree", Static)
        self._set_tree_classes()
        tree.update("… growing …")
        self._refresh_mode_line(suffix="thinking")
        self._ask(text)

    @work(exclusive=True, thread=True)
    def _ask(self, text: str) -> None:
        try:
            result = self.brain.ask(text)
        except BrainError as exc:
            self.call_from_thread(self._show_error, str(exc))
            return
        self.call_from_thread(self._show_result, result)

    def _ready_prompt(self) -> None:
        self._busy = False
        prompt = self.query_one("#prompt", Input)
        prompt.disabled = False
        prompt.focus()

    def _show_error(self, message: str) -> None:
        self._set_tree_classes("-error")
        self.query_one("#tree", Static).update(message)
        self._refresh_mode_line(suffix="error")
        self._ready_prompt()

    def _show_result(self, result: ClarifyResult | TreeResult) -> None:
        tree = self.query_one("#tree", Static)
        if isinstance(result, ClarifyResult):
            self._set_tree_classes("-clarify")
            tree.update(result.question)
            self._title_line = "clarify"
            self._refresh_mode_line(suffix="clarify")
        else:
            self._set_tree_classes()
            tree.update(self.brain.last_display)
            self._title_line = result.title
            self._refresh_mode_line(suffix=result.title)
        self._ready_prompt()

    def action_clear(self) -> None:
        if self._busy:
            return
        self.brain.clear()
        self._last_save_path = None
        self._title_line = ""
        self.query_one("#user-line", Static).update("")
        self.query_one("#tree", Static).update("")
        self._set_tree_classes()
        self._set_status("")
        self._refresh_mode_line()
        prompt = self.query_one("#prompt", Input)
        prompt.value = ""
        prompt.focus()

    def _display_path(self, path: Path) -> str:
        """Prefer ~/… when under home for a short, readable path."""
        try:
            resolved = path.expanduser().resolve()
            home = Path.home().resolve()
            if resolved == home or home in resolved.parents:
                return "~/" + resolved.relative_to(home).as_posix()
        except (OSError, ValueError):
            pass
        return str(path)

    def _set_status(self, message: str, *, kind: str | None = None, hold: float = 0) -> None:
        status = self.query_one("#status", Static)
        status.remove_class("-ok", "-err")
        if kind:
            status.add_class(f"-{kind}")
        status.update(message)
        if self._status_timer is not None:
            self._status_timer.stop()
            self._status_timer = None
        if hold > 0:
            self._status_timer = self.set_timer(hold, self._clear_status_style)

    def _clear_status_style(self) -> None:
        """After a brief highlight, dim the status but keep the path text."""
        status = self.query_one("#status", Static)
        status.remove_class("-ok", "-err")
        self._status_timer = None

    def action_save(self) -> None:
        if self._busy:
            return
        if not self.brain.last_tree:
            self._set_status("nothing to save yet — grow a tree first", kind="err", hold=4.0)
            return
        root = self.brain.last_tree.root
        directory = _save_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_status(f"save failed: {exc}", kind="err", hold=6.0)
            return

        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        path = directory / f"{_slug(root.name)}-{stamp}.md"
        body = to_markdown(root)
        # Append the ASCII tree as a fenced block for the visual form
        body += "\n## Tree\n\n```\n" + self.brain.last_display + "\n```\n"
        try:
            path.write_text(body, encoding="utf-8")
        except OSError as exc:
            self._set_status(f"save failed: {exc}", kind="err", hold=6.0)
            return

        self._last_save_path = path
        shown = self._display_path(path)
        self._set_status(f"saved · {shown}", kind="ok", hold=8.0)
        self._refresh_mode_line(suffix=f"saved · {path.name}")

    def action_export_html(self) -> None:
        if self._busy:
            return
        if not self.brain.last_tree:
            self._set_status("nothing to export yet — grow a tree first", kind="err", hold=4.0)
            return
        root = self.brain.last_tree.root
        directory = _save_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_status(f"export failed: {exc}", kind="err", hold=6.0)
            return

        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        name = _slug(root.name)
        path = directory / f"{name}-{stamp}.html"
        try:
            path.write_text(to_html(root), encoding="utf-8")
        except OSError as exc:
            self._set_status(f"export failed: {exc}", kind="err", hold=6.0)
            return

        shown = self._display_path(path)
        self._set_status(f"exported · {shown}", kind="ok", hold=8.0)
        self._refresh_mode_line(suffix=f"exported · {path.name}")
        webbrowser.open(f"file://{path.resolve()}")
