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

Needs an xAI API key:

```bash
export XAI_API_KEY=xai-...
# or: source ~/.grok/api.env
```

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
| Ctrl+S | Save current tree as Markdown |
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
| `XAI_API_KEY` | (required) |
| `IDEA_TREE_MODEL` | `grok-4.5` |
| `IDEA_TREE_BASE_URL` | `https://api.x.ai/v1` |
| `IDEA_TREE_MODE` | `moderate` |
| `IDEA_TREE_SAVE_DIR` | `~/idea-trees` |

## Philosophy

- Clarify only when needed; otherwise grow the tree
- Names and edges, not paragraphs
- Mode picks depth and language register
- Save when it clicks
