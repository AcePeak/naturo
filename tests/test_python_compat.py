"""Python version compatibility tests.

Verifies the codebase uses no Python 3.10+ syntax that would break on 3.9.
R-DEV-007 to R-DEV-011: Python 3.9-3.13 compatibility.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest


def _get_python_files():
    """Get all .py files in the naturo package."""
    pkg_dir = Path(__file__).parent.parent / "naturo"
    return list(pkg_dir.rglob("*.py"))


def _check_file_for_310_syntax(filepath):
    """Check a file for Python 3.10+ syntax patterns.

    Returns list of issues found.
    """
    issues = []
    source = filepath.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        issues.append(f"SyntaxError: {e}")
        return issues

    for node in ast.walk(tree):
        # Check for match/case (3.10+)
        if hasattr(ast, "Match") and isinstance(node, ast.Match):
            issues.append(
                f"Line {node.lineno}: match/case statement (requires Python 3.10+)"
            )

        # Check for X | Y union type in annotations (3.10+)
        # Only a problem if file doesn't have 'from __future__ import annotations'
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # This could be a union type annotation — check context
            # In runtime annotations without __future__, this breaks on 3.9
            pass  # Covered by __future__ import check below

    # Check for 'from __future__ import annotations' if file uses | in annotations
    has_future_annotations = "from __future__ import annotations" in source

    # Scan for bare 'X | Y' in function signatures (without __future__)
    if not has_future_annotations:
        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Look for type hints with | (e.g., 'str | None', 'int | str')
            if "def " in stripped or ": " in stripped:
                # Simple heuristic: look for ' | ' in potential type annotations
                # Skip comments and strings
                if "#" in stripped:
                    stripped = stripped[:stripped.index("#")]
                if " | " in stripped and (":" in stripped or "->" in stripped):
                    # Could be a union type without __future__
                    issues.append(
                        f"Line {i}: Possible bare union type '|' without "
                        "'from __future__ import annotations': {stripped.strip()}"
                    )

    return issues


class TestPython39Compatibility:
    """R-DEV-007: Python 3.9 compatibility — no 3.10+ syntax."""

    def test_no_match_case_statements(self):
        """R-DEV-007: No match/case statements in codebase (Python 3.10+ feature)."""
        for filepath in _get_python_files():
            source = filepath.read_text(encoding="utf-8")
            # Simple text search (AST check may miss some patterns)
            lines = source.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("match ") and stripped.endswith(":"):
                    pytest.fail(
                        f"{filepath}:{i}: match/case statement found "
                        f"(requires Python 3.10+)"
                    )

    def test_union_types_use_future_annotations(self):
        """R-DEV-008: Files using X|Y union types must have __future__ annotations."""
        for filepath in _get_python_files():
            issues = _check_file_for_310_syntax(filepath)
            if issues:
                pytest.fail(
                    f"{filepath.name}: Python 3.10+ syntax found:\n"
                    + "\n".join(f"  - {i}" for i in issues)
                )

    def test_no_walrus_in_non_comprehension(self):
        """R-DEV-009: Walrus operator (:=) is 3.8+ so OK, but verify no 3.10+ usage."""
        # Walrus operator is fine (3.8+), just verify it parses
        for filepath in _get_python_files():
            source = filepath.read_text(encoding="utf-8")
            try:
                compile(source, str(filepath), "exec")
            except SyntaxError as e:
                pytest.fail(f"{filepath}: SyntaxError: {e}")

    def test_no_exception_groups(self):
        """R-DEV-010: No ExceptionGroup or except* syntax (Python 3.11+ feature)."""
        for filepath in _get_python_files():
            source = filepath.read_text(encoding="utf-8")
            lines = source.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("except*"):
                    pytest.fail(
                        f"{filepath}:{i}: except* syntax found "
                        f"(requires Python 3.11+)"
                    )

    def test_no_tomllib_without_fallback(self):
        """R-DEV-011: tomllib usage must have fallback for Python < 3.11."""
        for filepath in _get_python_files():
            source = filepath.read_text(encoding="utf-8")
            if "import tomllib" in source and "sys.version_info" not in source:
                if "tomli" not in source:
                    pytest.fail(
                        f"{filepath}: Uses tomllib without fallback for Python < 3.11"
                    )

    def test_all_files_compile(self):
        """R-DEV-007: All Python files compile successfully."""
        for filepath in _get_python_files():
            source = filepath.read_text(encoding="utf-8")
            try:
                compile(source, str(filepath), "exec")
            except SyntaxError as e:
                pytest.fail(f"{filepath}: Failed to compile: {e}")
