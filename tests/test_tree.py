"""Unit tests for tree parse/render."""

from idea_tree.tree import (
    ClarifyResult,
    Node,
    TreeResult,
    parse_outline_tree,
    parse_response,
    render_tree,
    to_markdown,
    to_outline,
)


def test_render_tree_brackets_and_branches():
    root = Node(
        "Music",
        [
            Node("Genre", [Node("Jazz"), Node("Folk")]),
            Node("Form", [Node("Song"), Node("Suite")]),
        ],
    )
    out = render_tree(root)
    assert out.splitlines()[0] == "[Music]"
    assert "├───[Genre]" in out
    assert "└───[Form]" in out
    assert "└───[Folk]" in out


def test_parse_clarify():
    r = parse_response("CLARIFY\nWhich domain of gardening?")
    assert isinstance(r, ClarifyResult)
    assert "gardening" in r.question


def test_parse_outline_tree():
    raw = """TREE
Boat
  Hull
  Rig
    Mast
    Sail
  Keel
"""
    r = parse_response(raw)
    assert isinstance(r, TreeResult)
    assert r.root.name == "Boat"
    assert [c.name for c in r.root.children] == ["Hull", "Rig", "Keel"]
    assert r.root.children[1].children[0].name == "Mast"
    md = to_markdown(r.root)
    assert md.startswith("# Boat")
    assert "- Hull" in md


def test_parse_outline_with_brackets_and_art():
    raw = """TREE
[Camp]
├───[Shelter]
│   ├───[Tent]
│   └───[Hammock]
└───[Fire]
"""
    r = parse_response(raw)
    assert isinstance(r, TreeResult)
    assert r.root.name == "Camp"
    assert r.root.children[0].children[1].name == "Hammock"


def test_parse_json_still_works():
    raw = """TREE
{"root": "Boat", "children": [{"name": "Hull"}, {"name": "Rig", "children": [{"name": "Mast"}]}]}
"""
    r = parse_response(raw)
    assert isinstance(r, TreeResult)
    assert r.root.name == "Boat"
    assert r.root.children[1].children[0].name == "Mast"


def test_parse_json_trailing_comma_and_truncation():
    # trailing comma
    raw = '''TREE
{"root": "X", "children": [{"name": "Y"},],}
'''
    r = parse_response(raw)
    assert isinstance(r, TreeResult)
    assert r.root.children[0].name == "Y"

    # truncated mid-object — salvage what we can
    truncated = (
        'TREE\n{"root": "Camp", "children": [{"name": "Shelter", "children": '
        '[{"name": "Tent"}, {"name": "Ham'
    )
    r2 = parse_response(truncated)
    assert isinstance(r2, TreeResult)
    assert r2.root.name == "Camp"


def test_to_outline_roundtrip():
    root = Node("A", [Node("B", [Node("C")]), Node("D")])
    outline = to_outline(root)
    back = parse_outline_tree(outline)
    assert back.root.name == "A"
    assert back.root.children[0].children[0].name == "C"
