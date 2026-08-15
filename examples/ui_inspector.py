#!/usr/bin/env python3
"""Interactive UI tree exploration for a target application.

Reads the UI element tree with the in-process SDK, prints it, and lets you
inspect elements interactively — demonstrating the see -> find -> click
workflow without any subprocess.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python ui_inspector.py notepad
    python ui_inspector.py calculator --depth 3
    python ui_inspector.py chrome --cascade      # fused UIA+CDP+JAB+COM tree
"""

import argparse
import sys

import naturo


def print_tree(element: naturo.Element, depth: int = 0) -> int:
    """Print an element and its descendants; return the node count."""
    indent = "  " * depth
    name = element.name or ""
    print(f"{indent}[{element.role}]  {name}")
    count = 1
    for child in element.children:
        count += print_tree(child, depth + 1)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore UI element tree")
    parser.add_argument("app", help="Application name (e.g. notepad, calculator)")
    parser.add_argument("--depth", type=int, default=0,
                        help="Maximum tree depth (0 = unlimited, the default)")
    parser.add_argument("--cascade", action="store_true",
                        help="Fuse UIA + web (CDP) + Java (JAB) + Excel (COM)")
    args = parser.parse_args()

    print(f"Inspecting UI tree for '{args.app}'...\n")

    desktop = naturo.Desktop()
    root = desktop.see(app=args.app, depth=args.depth, cascade=args.cascade)
    if root is None:
        print(f"Failed to inspect {args.app}. Is it running?", file=sys.stderr)
        sys.exit(1)

    total = print_tree(root)
    print(f"\nFound {total} UI elements.")

    # Interactive exploration: search for elements by "Role:Name" selector.
    print("\n--- Interactive Mode ---")
    print("Enter a selector (e.g. Button:Save) to find an element, or 'q' to quit.\n")

    while True:
        try:
            query = input("Find> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if query.lower() in ("q", "quit", "exit"):
            break
        if not query:
            continue

        match = root.find(query)
        if match is not None:
            x, y, w, h = match.bounds
            print(f"  [{match.role}] {match.name!r}  "
                  f"bounds=({x},{y},{w},{h})  value={match.value!r}")
        else:
            print(f"  No element matching {query!r}.")

    print("Done.")


if __name__ == "__main__":
    main()
