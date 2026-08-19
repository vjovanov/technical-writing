#!/usr/bin/env python3
"""Render a template's inputs table as Markdown, straight from its manifest.

Keeps every README's inputs table in sync with the template it documents: the
table is generated from template.yaml rather than transcribed from it, so a
renamed input cannot leave stale documentation behind.
"""
import re
import sys
from pathlib import Path


def parse_manifest(text):
    """Minimal manifest reader — enough for the inputs table, no YAML dependency."""
    inputs, cur, in_inputs = [], None, False
    absorbing = None  # which key a block scalar is currently feeding

    for raw in text.split("\n"):
        if raw.startswith("inputs:"):
            in_inputs = True
            continue
        if not in_inputs:
            continue
        if raw and not raw.startswith(" ") and not raw.startswith("-"):
            break

        m = re.match(r"^  - name: (\S+)", raw)
        if m:
            cur = {"name": m.group(1), "type": "string", "default": None,
                   "description": "", "positional": None}
            inputs.append(cur)
            absorbing = None
            continue
        if cur is None:
            continue

        # A key at field indentation ends any block scalar being absorbed.
        m = re.match(r"^    ([a-z_]+): ?(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2).strip()
            absorbing = None
            if key in ("type", "positional"):
                cur[key] = val
            elif key == "default":
                cur["default"] = "block" if val in ("|", ">-", ">") else val
                if val in ("|", ">-", ">"):
                    absorbing = "_skip"
            elif key == "description":
                if val in ("|", ">-", ">"):
                    cur["description"] = ""
                    absorbing = "description"
                else:
                    cur["description"] = val
            continue

        # Continuation lines of whatever block scalar is open.
        if absorbing == "description" and raw.strip():
            cur["description"] = (cur["description"] + " " + raw.strip()).strip()

    return inputs


def main():
    manifest = Path(sys.argv[1])
    rows = parse_manifest(manifest.read_text())
    print("| Input | Type | Default | Description |")
    print("|---|---|---|---|")
    for i in rows:
        default = i["default"]
        if default is None:
            req = "**required**"
        elif default == "block":
            req = "see `template.yaml`"
        elif default in ('""', "''"):
            req = "_empty_"
        elif default == "[]":
            req = "_empty list_"
        else:
            req = f"`{default}`" if len(str(default)) < 60 else "see template.yaml"
        desc = i["description"].replace("|", "\\|")
        name = f"`{i['name']}`"
        if i.get("positional"):
            name += f" (positional {i['positional']})"
        print(f"| {name} | {i['type']} | {req} | {desc} |")


if __name__ == "__main__":
    main()
