"""Mode resolution and prompt tests."""

import pytest

from idea_tree.modes import cycle_mode, normalize_mode
from idea_tree.prompt import build_system_prompt


def test_normalize_aliases():
    assert normalize_mode("mod") == "moderate"
    assert normalize_mode("exhaustive") == "exhaustive"
    assert normalize_mode("parlance") == "common"
    assert normalize_mode("common person") == "common"
    assert normalize_mode("only-common") == "common"
    assert normalize_mode(None) == "moderate"


def test_cycle():
    assert cycle_mode("moderate") == "exhaustive"
    assert cycle_mode("exhaustive") == "common"
    assert cycle_mode("common") == "moderate"


def test_prompts_differ():
    m = build_system_prompt("moderate")
    e = build_system_prompt("exhaustive")
    c = build_system_prompt("common")
    assert "MODERATE" in m
    assert "EXHAUSTIVE" in e
    assert "COMMON PARLANCE" in c
    assert "jargon" in c.lower() or "everyday" in c.lower()


def test_bad_mode():
    with pytest.raises(ValueError):
        normalize_mode("quantum")
