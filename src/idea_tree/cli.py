"""CLI entry for idea-tree."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .app import IdeaTreeApp
from .brain import Brain, BrainError, DEFAULT_MODEL
from .modes import MODE_ORDER


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="idea-tree",
        description="Minimalist CLI that taxonomifies ideas into visual trees",
    )
    p.add_argument(
        "--model",
        default=None,
        help=f"xAI model id (default: env IDEA_TREE_MODEL or {DEFAULT_MODEL})",
    )
    p.add_argument(
        "-m",
        "--mode",
        default=None,
        metavar="MODE",
        help=(
            "taxonomy mode: moderate | exhaustive | common "
            f"(default: env IDEA_TREE_MODE or moderate; cycle in-app with ctrl+t). "
            f"order: {' → '.join(MODE_ORDER)}"
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"idea-tree {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        brain = Brain.from_env(model=args.model, mode=args.mode)
    except BrainError as exc:
        print(f"idea-tree: {exc}", file=sys.stderr)
        return 1

    IdeaTreeApp(brain).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
