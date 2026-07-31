# idea-tree

A minimalist CLI that taxonomifies ideas into a visual ontology tree.

Type near the center of the screen. If the idea is ambiguous, you get a short
clarifying question. Once clear, the app expands the idea into named categories
and edges — mainly labels, not essays.

## Setup

```bash
cd ~/idea-tree
pip install -e .
# or: uv pip install -e .
```

Needs at least one API key:

```bash
export XAI_API_KEY=xai-...          # xAI (default)
export IDEA_TREE_OPENAI_KEY=sk-...  # OpenAI (switch with Ctrl+P)
```

Toggle between available providers with **Ctrl+P**. The app auto-detects which
keys are available and skips providers with missing or mismatched keys
(`OPENAI_API_KEY` is only used as a fallback if it starts with `sk-`, so Cohere
or other compat keys never hit `api.openai.com`).

## Run

```bash
idea-tree
idea-tree --mode exhaustive
idea-tree -m common
idea-tree --model grok-4.5
```

| Key | Action |
|-----|--------|
| Enter | Send / expand |
| **Ctrl+T** | Cycle mode: moderate → exhaustive → common parlance |
| **Ctrl+P** | Cycle provider: xAI ↔ OpenAI |
| Ctrl+S | Save current tree as Markdown |
| Ctrl+E | Export tree as interactive HTML (opens in browser) |
| Ctrl+L | Clear history + tree |
| Esc / Ctrl+C | Quit |

### Modes

| Mode | What it does |
|------|----------------|
| **moderate** (default) | Focused tree, depth ~2–4, ≤~40 nodes |
| **exhaustive** | Wide/deep map of the real edges of the idea |
| **common** | Everyday plain-person names only — no jargon |

Cycle with **Ctrl+T** (history clears so the next grow uses the new stance).
Note: Ctrl+M is the same as Enter in most terminals, so mode uses Ctrl+T.

## Env

| Variable | Default |
|----------|---------|
| `XAI_API_KEY` | (required for xAI) |
| `IDEA_TREE_OPENAI_KEY` | (required for OpenAI) |
| `IDEA_TREE_BASE_URL` | `https://api.x.ai/v1` (overrides the active provider's base URL at startup) |
| `IDEA_TREE_PROVIDER` | first available in xAI → OpenAI order |
| `IDEA_TREE_MODEL` | per-provider default (`grok-4.5` / `gpt-4o`) |
| `IDEA_TREE_MODE` | `moderate` |
| `IDEA_TREE_SAVE_DIR` | `~/idea-trees` |
| `IDEA_TREE_THEME` | `dark` (HTML export default; `light` for light) |

`--model` only applies to the provider selected at startup; cycling with Ctrl+P
switches to each provider's own default model.

## HTML export

`Ctrl+E` writes `~/idea-trees/<slug>-<stamp>.html` and opens it in your browser.
The viewer is a sprite-based canvas renderer (pre-baked glow, cached background,
30 Hz physics, DPR cap) so it stays smooth even on low-RAM machines.

Exported HTML has a sun/moon toggle; choice persists in `localStorage` and
respects `?theme=light|dark` on the URL. `IDEA_TREE_THEME` sets the first-load
default for exports.

## Development

```bash
python -m pytest        # 11 tests
ruff check src tests    # lint (line-length 100, py312)
```

Standalone demos live in `demo/` (`sensory-deprivation.html` dark,
`sensory-deprivation-light.html` light), regenerated from
`src/idea_tree/data/thought-tree-template.html`.

## Philosophy

- Clarify only when needed; otherwise grow the tree
- Names and edges, not paragraphs
- Mode picks depth and language register
- Save when it clicks
