"""Taxonomy depth / language modes for idea-tree."""

from __future__ import annotations

from dataclasses import dataclass

# Canonical keys in cycle order
MODE_ORDER = ("moderate", "exhaustive", "common")

# Aliases → canonical
_ALIASES: dict[str, str] = {
    "moderate": "moderate",
    "mod": "moderate",
    "default": "moderate",
    "balanced": "moderate",
    "exhaustive": "exhaustive",
    "full": "exhaustive",
    "deep": "exhaustive",
    "complete": "exhaustive",
    "common": "common",
    "parlance": "common",
    "plain": "common",
    "everyday": "common",
    "folk": "common",
    "lay": "common",
    "layperson": "common",
    "only-common": "common",
    "only_common": "common",
    "common-person": "common",
    "common_person": "common",
    "common parlance": "common",
}


@dataclass(frozen=True)
class ModeSpec:
    key: str
    label: str
    short: str
    max_tokens: int
    guidance: str


MODES: dict[str, ModeSpec] = {
    "moderate": ModeSpec(
        key="moderate",
        label="moderate",
        short="mod",
        max_tokens=2500,
        guidance="""\
Depth mode: MODERATE (default).
- Depth 2–4 levels; focused breadth (roughly ≤40 total nodes).
- Cover the main kinds, parts, and facets without encyclopedic detail.
- Prefer a clean complete tree over a dump that may get cut off.
- Stop when further branches would be filler or near-duplicates.
""",
    ),
    "exhaustive": ModeSpec(
        key="exhaustive",
        label="exhaustive",
        short="exh",
        max_tokens=4500,
        guidance="""\
Depth mode: EXHAUSTIVE.
- Push breadth and depth hard: aim to map the real edges of the idea.
- Depth often 3–6 levels; many siblings where the domain has real kinds.
- Include less-obvious facets: edge cases, rare subtypes, technical branches,
  opposites, stages, roles, media, contexts — still names only, no essays.
- Still avoid pure filler and duplicate renames of the same node.
- Prefer completeness over brevity; a large tree is expected.
""",
    ),
    "common": ModeSpec(
        key="common",
        label="common parlance",
        short="common",
        max_tokens=2000,
        guidance="""\
Depth mode: COMMON PARLANCE only.
- Use only everyday, plain-person language for every node name.
- No jargon, academic terms, Latinisms, specialist taxonomy, or insider slang
  unless that word is truly common in ordinary conversation.
- Prefer words a non-expert would say out loud: "heart doctor" not "cardiologist"
  only when the common form is clearer; otherwise use the ordinary word people use.
- Shallower is fine (depth 2–3). Fewer nodes. Familiar buckets only.
- If a technical distinction has no common name, skip it or fold it under a
  plain umbrella — do not invent fancy labels.
""",
    ),
}


def normalize_mode(value: str | None) -> str:
    """Return a canonical mode key; default moderate."""
    if value is None:
        return "moderate"
    raw = " ".join(value.strip().lower().replace("_", "-").split())
    if not raw:
        return "moderate"
    if raw in _ALIASES:
        return _ALIASES[raw]
    # prefix match
    for alias, key in _ALIASES.items():
        if alias.startswith(raw) or raw.startswith(alias):
            return key
    raise ValueError(
        f"unknown mode {value!r}; use: moderate | exhaustive | common"
    )


def cycle_mode(current: str) -> str:
    key = normalize_mode(current)
    i = MODE_ORDER.index(key)
    return MODE_ORDER[(i + 1) % len(MODE_ORDER)]


def mode_spec(key: str | None) -> ModeSpec:
    return MODES[normalize_mode(key)]
