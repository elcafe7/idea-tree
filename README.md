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

Toggle between available providers with **Ctrl+P**. The app auto-detects which keys are available and skips providers with missing or mismatched keys.

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
| `IDEA_TREE_MODEL` | per-provider default |
| `IDEA_TREE_MODE` | `moderate` |
| `IDEA_TREE_SAVE_DIR` | `~/idea-trees` |
| `IDEA_TREE_THEME` | `dark` (HTML export default; `light` for light) |

Exported HTML has a sun/moon toggle; choice persists in `localStorage` and
respects `?theme=light|dark` on the URL. `IDEA_TREE_THEME` sets the first-load
default for exports.

## Philosophy

- Clarify only when needed; otherwise grow the tree
- Names and edges, not paragraphs
- Mode picks depth and language register
- Save when it clicks
