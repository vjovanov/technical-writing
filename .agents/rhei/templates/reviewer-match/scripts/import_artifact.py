#!/usr/bin/env python3
"""
Import an upstream pipeline artifact into this workspace, validating it first.

Rhei artifact contracts may not reference paths outside the workspace root, so a
downstream template cannot simply declare the previous template's output as an
input. Composition happens here instead: this program copies the upstream file
in and refuses to do so unless it conforms to the schema and is the artifact the
consumer actually expects.

Doing the check at the boundary is the point. A stale, truncated, or
wrong-artifact file discovered here costs one program invocation; discovered
after the fan-out it costs a full multi-model review, and may not be discovered
at all — a reviewer reading a half-written paper.json produces confident,
plausible, wrong output.

Usage
    import_artifact.py --source <path> --dest <path> \\
        --expect-artifact <name> --schema-dir <dir> [--optional]

Exit codes
    0  imported (or absent and --optional)
    1  the source is missing, or does not conform to its schema
    2  usage or I/O error
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_artifact import load_json, validate, SchemaError, write_result  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description="Import and validate an upstream pipeline artifact.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--source", required=True, help="Upstream artifact, typically in another workspace")
    ap.add_argument("--dest", required=True, help="Where to place it inside this workspace")
    ap.add_argument("--expect-artifact", required=True, help="The `artifact` value this consumer requires")
    ap.add_argument("--schema-dir", required=True, type=Path)
    ap.add_argument(
        "--optional",
        action="store_true",
        help="Treat a missing source as success, so the workflow can degrade instead of stopping",
    )
    args = ap.parse_args()

    source = Path(args.source).expanduser()
    dest = Path(args.dest)

    if not source.exists():
        if args.optional:
            msg = (
                f"Optional input `{args.expect_artifact}` was not supplied "
                f"(`{source}` does not exist). Continuing without it."
            )
            print(f"- {msg}")
            write_result(f"## Artifact import — `{args.expect_artifact}`\n\n{msg}\n")
            sys.exit(0)
        msg = (
            f"required input `{args.expect_artifact}` not found at `{source}`. "
            f"Point the corresponding template input at the upstream workspace that produced it."
        )
        write_result(f"## Artifact import — `{args.expect_artifact}`\n\n**Missing.** {msg}\n")
        print(f"error: {msg}", file=sys.stderr)
        sys.exit(1)

    instance = load_json(source, "source artifact")

    declared = instance.get("artifact") if isinstance(instance, dict) else None
    if declared != args.expect_artifact:
        msg = (
            f"artifact mismatch importing `{source}`: expected "
            f"{args.expect_artifact!r}, file declares {declared!r}. "
            f"A wrong upstream workspace is wired into this input."
        )
        write_result(f"## Artifact import — `{args.expect_artifact}`\n\n**Wrong artifact.** {msg}\n")
        print(f"error: {msg}", file=sys.stderr)
        sys.exit(1)

    schema_path = args.schema_dir / f"{args.expect_artifact}.schema.json"
    schema = load_json(schema_path, "schema")

    try:
        errors = validate(instance, schema)
    except SchemaError as e:
        print(f"error: malformed schema {schema_path}: {e}", file=sys.stderr)
        sys.exit(2)

    header = (
        f"## Artifact import — `{args.expect_artifact}`\n\n"
        f"- Source: `{source}`\n- Destination: `{dest}`\n"
        f"- Schema: `{schema_path}`\n"
    )

    if errors:
        lines = "\n".join(f"- `{p}` — {m}" for p, m in errors)
        write_result(header + f"\n**Rejected — {len(errors)} schema violation(s):**\n\n{lines}\n")
        print(f"✗ rejected: {source} ({len(errors)} schema violation(s))", file=sys.stderr)
        for p, m in errors:
            print(f"    {p}: {m}", file=sys.stderr)
        sys.exit(1)

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    except OSError as e:
        print(f"error: cannot write {dest}: {e}", file=sys.stderr)
        sys.exit(2)

    write_result(header + "\n**Imported.** The artifact conforms to its schema.\n")
    print(f"✓ imported: {source} -> {dest}")
    sys.exit(0)


if __name__ == "__main__":
    main()
