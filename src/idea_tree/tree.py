"""Tree model, parsing, and ASCII rendering."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Node:
    name: str
    children: list[Node] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class TreeResult:
    root: Node

    @property
    def title(self) -> str:
        return self.root.name


@dataclass
class ClarifyResult:
    question: str


ParseResult = TreeResult | ClarifyResult


class ParseError(ValueError):
    """Model output could not be parsed."""


_SMART_QUOTES = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
)


def bracket(name: str) -> str:
    name = name.strip()
    if name.startswith("[") and name.endswith("]"):
        return name
    return f"[{name}]"


def strip_brackets(name: str) -> str:
    name = name.strip()
    if len(name) >= 2 and name.startswith("[") and name.endswith("]"):
        return name[1:-1].strip()
    return name


def render_tree(root: Node) -> str:
    """Render a vertical tree with [names] and branch connectors."""
    lines: list[str] = [bracket(root.name)]
    _render_children(root.children, lines, prefix="")
    return "\n".join(lines)


def _render_children(children: list[Node], lines: list[str], prefix: str) -> None:
    n = len(children)
    for i, child in enumerate(children):
        last = i == n - 1
        branch = "└───" if last else "├───"
        lines.append(f"{prefix}{branch}{bracket(child.name)}")
        extension = "    " if last else "│   "
        if child.children:
            _render_children(child.children, lines, prefix + extension)


def render_paths(root: Node, max_paths: int = 12) -> list[str]:
    """Optional horizontal path chains: [a]----[b]----[c]."""
    paths: list[list[str]] = []

    def walk(node: Node, trail: list[str]) -> None:
        here = trail + [node.name]
        if not node.children:
            paths.append(here)
            return
        for c in node.children:
            walk(c, here)

    walk(root, [])
    out: list[str] = []
    for path in paths[:max_paths]:
        out.append("----".join(bracket(p) for p in path))
    if len(paths) > max_paths:
        out.append(f"… +{len(paths) - max_paths} more paths")
    return out


def to_markdown(root: Node) -> str:
    lines = [f"# {root.name}", ""]
    if not root.children:
        lines.append(f"- {root.name}")
    else:
        for child in root.children:
            _md_node(child, lines, depth=0)
    lines.append("")
    return "\n".join(lines)


def _md_node(node: Node, lines: list[str], depth: int) -> None:
    indent = "  " * depth
    lines.append(f"{indent}- {node.name}")
    for child in node.children:
        _md_node(child, lines, depth + 1)


def to_outline(root: Node) -> str:
    """Canonical outline form used in history / model preference."""
    lines = [root.name]
    _outline_children(root.children, lines, depth=1)
    return "\n".join(lines)


def _outline_children(children: list[Node], lines: list[str], depth: int) -> None:
    pad = "  " * depth
    for child in children:
        lines.append(f"{pad}{child.name}")
        if child.children:
            _outline_children(child.children, lines, depth + 1)


def to_html(root: Node, theme: str | None = None) -> str:
    raw_theme = (theme or os.environ.get("IDEA_TREE_THEME", "")).strip().lower()
    if raw_theme not in ("dark", "light"):
        raw_theme = "dark"
    _tmpl = Path(__file__).parent / "data" / "thought-tree-template.html"
    return (
        _tmpl.read_text(encoding="utf-8")
        .replace("__TREE_TITLE__", root.name)
        .replace("__TREE_JSON__", json.dumps(root.to_dict(), indent=2))
        .replace("__TREE_THEME__", json.dumps(raw_theme))
    )


def node_from_dict(data: Any) -> Node:
    if isinstance(data, str):
        return Node(name=data.strip())
    if not isinstance(data, dict):
        raise ParseError("tree node must be object or string")
    name = data.get("name") or data.get("root")
    if not name or not isinstance(name, str):
        raise ParseError("tree node missing name")
    raw_children = data.get("children") or []
    if not isinstance(raw_children, list):
        raise ParseError("children must be a list")
    children = [_child_from(item) for item in raw_children]
    return Node(name=name.strip(), children=children)


def _child_from(item: Any) -> Node:
    if isinstance(item, str):
        return Node(name=item.strip())
    if isinstance(item, dict):
        return node_from_dict(item)
    raise ParseError("invalid child node")


def tree_from_payload(data: dict[str, Any]) -> TreeResult:
    if "root" in data and isinstance(data["root"], str):
        root = Node(
            name=data["root"].strip(),
            children=[_child_from(c) for c in (data.get("children") or [])],
        )
        return TreeResult(root=root)
    if "root" in data and isinstance(data["root"], dict):
        return TreeResult(root=node_from_dict(data["root"]))
    if "name" in data:
        return TreeResult(root=node_from_dict(data))
    raise ParseError("TREE json missing root")


def parse_response(text: str) -> ParseResult:
    """Parse model output into ClarifyResult or TreeResult."""
    raw = text.strip()
    if not raw:
        raise ParseError("empty response")

    # Strip accidental fences
    raw = re.sub(r"^```(?:json|text|tree)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw).strip()

    upper = raw.upper()
    if upper.startswith("CLARIFY"):
        body = raw.split("\n", 1)
        question = body[1].strip() if len(body) > 1 else ""
        if not question:
            rest = raw[7:].strip(" \t:-")
            question = rest
        if not question:
            raise ParseError("empty clarify question")
        return ClarifyResult(question=question)

    body = raw
    if upper.startswith("TREE"):
        parts = raw.split("\n", 1)
        body = parts[1].strip() if len(parts) > 1 else ""
        if not body:
            raise ParseError("TREE missing body")

    # Prefer outline (primary format). JSON is a fallback for older replies.
    errors: list[str] = []
    if not body.lstrip().startswith("{"):
        try:
            return parse_outline_tree(body)
        except ParseError as exc:
            errors.append(str(exc))
    else:
        try:
            return _parse_json_tree(body)
        except ParseError as exc:
            errors.append(str(exc))
        try:
            return parse_outline_tree(body)
        except ParseError as exc:
            errors.append(str(exc))

    # Bare JSON without TREE header
    if raw.lstrip().startswith("{"):
        try:
            return _parse_json_tree(raw)
        except ParseError as exc:
            errors.append(str(exc))

    # Outline without TREE header
    try:
        return parse_outline_tree(raw)
    except ParseError as exc:
        errors.append(str(exc))

    # Plain clarifying question fallback
    if "?" in raw and len(raw) < 280 and "\n{" not in raw and raw.count("\n") < 3:
        return ClarifyResult(question=raw)

    detail = errors[-1] if errors else "unknown"
    raise ParseError(f"could not parse model response ({detail})")


def parse_outline_tree(text: str) -> TreeResult:
    """Parse indented outline into a tree.

    Indent is 2 spaces (or a tab) per level. Optional leading [brackets],
    bullets, or tree-drawing characters are stripped.
    """
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        # Skip JSON-looking lines if mixed garbage
        if raw_line.strip() in {"{", "}", "[", "]", "},", "],"}:
            continue
        if re.match(r'^\s*"[^"]+"\s*:', raw_line):
            raise ParseError("outline looks like json keys")

        expanded = raw_line.expandtabs(2)
        # Convert box-drawing into spaces so depth still tracks columns
        cleaned = expanded
        for ch in "│|":
            cleaned = cleaned.replace(ch, " ")
        cleaned = re.sub(r"[├└]", " ", cleaned)
        cleaned = re.sub(r"[─—–]+", " ", cleaned)

        stripped_left = cleaned.lstrip(" ")
        indent = len(cleaned) - len(stripped_left)

        name = stripped_left.strip()
        name = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", name)
        name = name.strip(" \t-")
        name = strip_brackets(name)
        name = name.rstrip(",").strip()
        if not name or name in {"children", "name", "root"}:
            continue
        if re.fullmatch(r"[{}\[\]\",:]+", name):
            continue
        lines.append((indent, name))

    if not lines:
        raise ParseError("empty outline tree")

    # Normalize indents to ranks
    indents = sorted({i for i, _ in lines})
    rank = {v: i for i, v in enumerate(indents)}

    root_name = lines[0][1]
    root = Node(name=root_name)
    stack: list[tuple[int, Node]] = [(0, root)]

    for indent, name in lines[1:]:
        level = rank[indent]
        # Pop to parent
        while stack and stack[-1][0] >= level:
            stack.pop()
        if not stack:
            # Sibling of root at same indent — treat as child of root
            stack = [(0, root)]
            level = 1
        parent = stack[-1][1]
        node = Node(name=name)
        parent.children.append(node)
        stack.append((level, node))

    return TreeResult(root=root)


def _parse_json_tree(json_text: str) -> TreeResult:
    data = _loads_json_lenient(json_text)
    if not isinstance(data, dict):
        raise ParseError("TREE json must be an object")
    return tree_from_payload(data)


def _loads_json_lenient(json_text: str) -> Any:
    """Parse JSON with repairs for common model mistakes / truncation."""
    candidates = _json_candidates(json_text)
    last_err: Exception | None = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
    if last_err:
        raise ParseError(f"invalid TREE json: {last_err}") from last_err
    raise ParseError("invalid TREE json")


def _json_candidates(json_text: str) -> list[str]:
    text = json_text.strip().translate(_SMART_QUOTES)
    # Drop markdown fences if still present mid-body
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()

    start = text.find("{")
    if start < 0:
        return []
    text = text[start:]

    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(text)
    add(_repair_json(text))
    # Slice to last complete-looking closing brace after repairs
    repaired = _repair_json(text)
    add(repaired)
    # Truncation salvage: close open braces/brackets
    add(_close_truncated_json(text))
    add(_close_truncated_json(repaired))
    return out


def _repair_json(text: str) -> str:
    s = text
    # Trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Python-ish True/False/None (rare)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    return s


def _close_truncated_json(text: str) -> str:
    """Best-effort close of truncated JSON so partial trees still parse."""
    s = _repair_json(text).rstrip()
    # If we ended mid-string, close the string
    if s.count('"') % 2 == 1:
        s += '"'

    # Drop a dangling incomplete key/value fragment after last comma/brace
    # e.g. `{"name": "Foo", "chil` or `,"name":`
    s = re.sub(r",\s*\"[^\"]*$", "", s)
    s = re.sub(r",\s*$", "", s)
    s = re.sub(r":\s*$", ': ""', s)

    opens: list[str] = []
    in_str = False
    escape = False
    for ch in s:
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            opens.append(ch)
        elif ch == "}":
            if opens and opens[-1] == "{":
                opens.pop()
        elif ch == "]" and opens and opens[-1] == "[":
            opens.pop()

    # Close in reverse order
    closing = []
    for ch in reversed(opens):
        closing.append("}" if ch == "{" else "]")
    return s + "".join(closing)
