#!/usr/bin/env python3
"""Generate CLI reference documentation from Click command definitions.

Usage:
    python scripts/generate_cli_reference.py > docs/CLI_REFERENCE.md

Introspects all registered Click commands in naturo.cli and produces
a comprehensive Markdown reference with options, arguments, and examples.
"""

from __future__ import annotations

from datetime import datetime, timezone

import click

from naturo.cli import main


def _format_option(param: click.Option) -> str:
    """Format a single Click option as a Markdown table row."""
    decls = ", ".join(f"`{d}`" for d in param.opts + param.secondary_opts)
    help_text = (param.help or "").replace("|", "\\|").replace("\n", " ").strip()
    if param.default is not None and param.default != () and not param.is_flag:
        default_str = str(param.default)
        # Filter out internal sentinel values, unhelpful defaults,
        # and avoid duplicating defaults already mentioned in help text
        if (
            "Sentinel" not in default_str
            and "UNSET" not in default_str
            and "default" not in help_text.lower()
        ):
            help_text += f" (default: `{param.default}`)"
    if param.required:
        help_text += " **required**"
    type_name = param.type.name if hasattr(param.type, "name") else str(param.type)
    if isinstance(param.type, click.Choice):
        type_name = "{" + ", ".join(param.type.choices) + "}"
    return f"| {decls} | {type_name} | {help_text} |"


def _format_argument(param: click.Argument) -> str:
    """Format a single Click argument as a Markdown table row."""
    name = param.name.upper() if param.name else "ARG"
    required = "yes" if param.required else "no"
    type_name = param.type.name if hasattr(param.type, "name") else str(param.type)
    return f"| `{name}` | {type_name} | {required} |"


def _extract_examples(help_text: str) -> list[str]:
    """Extract example lines from a Click command's help/docstring."""
    examples = []
    in_example = False
    for line in (help_text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("example") or stripped.lower().startswith("usage:"):
            in_example = True
            continue
        if in_example:
            if stripped.startswith("naturo "):
                examples.append(stripped)
            elif stripped == "" and examples:
                in_example = False
            elif stripped and not stripped.startswith("naturo") and not stripped.startswith("#"):
                # description line after example, skip
                pass
    return examples


def _render_command(
    cmd: click.Command,
    path: list[str],
    *,
    include_hidden: bool = False,
) -> str:
    """Render a single command as Markdown."""
    full_name = " ".join(path)
    lines: list[str] = []

    # Heading level based on depth
    level = min(len(path) + 1, 4)
    lines.append(f"{'#' * level} `naturo {full_name}`")
    lines.append("")

    # Description
    help_text = cmd.help or cmd.short_help or ""
    # First paragraph as description
    desc_lines = []
    for line in help_text.splitlines():
        if line.strip() == "" and desc_lines:
            break
        if line.strip():
            desc_lines.append(line.strip())
    if desc_lines:
        lines.append(" ".join(desc_lines))
        lines.append("")

    # Deprecation notice
    if cmd.deprecated:
        lines.append("> **Deprecated.** This command may be removed in a future version.")
        lines.append("")

    # Arguments
    arguments = [p for p in cmd.params if isinstance(p, click.Argument)]
    if arguments:
        lines.append("**Arguments:**")
        lines.append("")
        lines.append("| Name | Type | Required |")
        lines.append("|------|------|----------|")
        for arg in arguments:
            lines.append(_format_argument(arg))
        lines.append("")

    # Options (exclude hidden unless requested)
    options = [
        p for p in cmd.params
        if isinstance(p, click.Option)
        and p.name != "help"
        and (include_hidden or not p.hidden)
    ]
    if options:
        lines.append("**Options:**")
        lines.append("")
        lines.append("| Flag | Type | Description |")
        lines.append("|------|------|-------------|")
        for opt in options:
            lines.append(_format_option(opt))
        lines.append("")

    # Examples from docstring
    examples = _extract_examples(help_text)
    if examples:
        lines.append("**Examples:**")
        lines.append("")
        lines.append("```bash")
        for ex in examples:
            lines.append(ex)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def _walk_commands(
    group: click.BaseCommand,
    path: list[str] | None = None,
    *,
    include_hidden: bool = False,
) -> list[tuple[list[str], click.BaseCommand]]:
    """Walk all commands recursively, returning (path, command) pairs."""
    if path is None:
        path = []
    results: list[tuple[list[str], click.BaseCommand]] = []

    if isinstance(group, click.Group):
        for name, cmd in sorted(group.commands.items()):
            if cmd.hidden and not include_hidden:
                continue
            cmd_path = path + [name]
            results.append((cmd_path, cmd))
            if isinstance(cmd, click.Group):
                results.extend(
                    _walk_commands(cmd, cmd_path, include_hidden=include_hidden)
                )
    return results


def generate_reference(*, include_hidden: bool = False) -> str:
    """Generate the full CLI reference as Markdown."""
    lines: list[str] = []

    # Header
    lines.append("# CLI Reference")
    lines.append("")
    lines.append(
        "Complete reference for all `naturo` commands. "
        "Auto-generated from Click command definitions."
    )
    lines.append("")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.append(f"*Generated: {now}*")
    lines.append("")

    # Global options
    lines.append("## Global Options")
    lines.append("")
    lines.append("These options can be passed to any command:")
    lines.append("")
    lines.append("```bash")
    lines.append("naturo [--json] [--verbose] [--log-level LEVEL] COMMAND [ARGS]")
    lines.append("```")
    lines.append("")
    lines.append("| Flag | Description |")
    lines.append("|------|-------------|")
    lines.append("| `--version` | Show version and exit |")
    lines.append("| `-j`, `--json` | JSON output for all commands |")
    lines.append("| `-v`, `--verbose` | Verbose logging |")
    lines.append("| `--log-level` | Log level: trace, debug, info, warning, error |")
    lines.append("| `--help` | Show help and exit |")
    lines.append("")

    # Table of contents
    lines.append("## Commands")
    lines.append("")

    all_commands = _walk_commands(main, include_hidden=include_hidden)

    # Group by category
    categories: dict[str, list[tuple[list[str], click.BaseCommand]]] = {
        "See (Inspect UI)": [],
        "Act (Interact)": [],
        "App & Window Management": [],
        "System": [],
        "Tools": [],
    }

    see_cmds = {"see", "capture", "find", "list", "get", "highlight", "menu-inspect"}
    act_cmds = {"click", "type", "press", "scroll", "drag", "move", "set"}
    app_cmds = {"app", "window", "dialog", "wait", "diff"}
    system_cmds = {"desktop", "taskbar", "tray"}
    # Everything else goes to Tools

    for cmd_path, cmd in all_commands:
        top = cmd_path[0]
        if top in see_cmds:
            categories["See (Inspect UI)"].append((cmd_path, cmd))
        elif top in act_cmds:
            categories["Act (Interact)"].append((cmd_path, cmd))
        elif top in app_cmds:
            categories["App & Window Management"].append((cmd_path, cmd))
        elif top in system_cmds:
            categories["System"].append((cmd_path, cmd))
        else:
            categories["Tools"].append((cmd_path, cmd))

    # TOC
    for cat_name, cmds in categories.items():
        if not cmds:
            continue
        lines.append(f"### {cat_name}")
        lines.append("")
        for cmd_path, cmd in cmds:
            full = " ".join(cmd_path)
            anchor = f"naturo-{full.replace(' ', '-')}"
            short = cmd.short_help or (cmd.help or "").split("\n")[0][:80]
            indent = "  " * (len(cmd_path) - 1)
            lines.append(f"{indent}- [`naturo {full}`](#{anchor}) — {short}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Full reference
    for cat_name, cmds in categories.items():
        if not cmds:
            continue
        lines.append(f"## {cat_name}")
        lines.append("")
        for cmd_path, cmd in cmds:
            lines.append(_render_command(cmd, cmd_path, include_hidden=include_hidden))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_reference())
