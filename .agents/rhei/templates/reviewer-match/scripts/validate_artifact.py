#!/usr/bin/env python3
"""
Validate a pipeline artifact against its JSON Schema.

Every handoff between paper-pipeline templates is a JSON file with a declared
shape. This script is what makes that contract real: rhei program states run it
between an agent that writes an artifact and the task that consumes it, so a
malformed handoff stops the workflow at its source instead of surfacing as a
confusing failure three templates downstream.

Dependency-free on purpose. It implements the JSON Schema subset the pipeline
schemas use, rather than requiring `jsonschema` to be installed on every machine
that runs a review.

Supported keywords
    $ref (local "#/$defs/..." only), $defs, type, enum, const,
    properties, required, additionalProperties, patternProperties,
    items, prefixItems, minItems, maxItems, uniqueItems,
    minimum, maximum, exclusiveMinimum, exclusiveMaximum,
    minLength, maxLength, pattern, format (annotation only),
    oneOf, anyOf, allOf, not, nullable

Unsupported keywords are reported rather than ignored, so a schema cannot
silently under-validate.

Usage
    validate_artifact.py --schema <schema.json> --instance <artifact.json>
    validate_artifact.py --schema-dir <dir> --instance <artifact.json>   # by `artifact` field
    validate_artifact.py --self-test

Exit codes
    0  valid
    1  invalid (schema violations, reported to stdout and the rhei result file)
    2  usage or I/O error
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SUPPORTED = {
    "$schema", "$id", "$ref", "$defs", "$comment", "title", "description",
    "default", "examples", "deprecated", "format",
    "type", "enum", "const", "nullable",
    "properties", "required", "additionalProperties", "patternProperties",
    "items", "prefixItems", "minItems", "maxItems", "uniqueItems",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern",
    "oneOf", "anyOf", "allOf", "not",
}

TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaError(Exception):
    """The schema itself is malformed or uses an unsupported keyword."""


def type_name(value):
    for name in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if TYPE_CHECKS[name](value):
            return name
    return type(value).__name__


def resolve_ref(ref, root):
    """Resolve a local '#/$defs/name' reference against the root schema."""
    if not ref.startswith("#/"):
        raise SchemaError(f"only local '#/...' refs are supported, got {ref!r}")
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise SchemaError(f"unresolvable ref {ref!r}")
        node = node[part]
    return node


def validate(instance, schema, root=None, path="$", errors=None):
    """Validate `instance` against `schema`, collecting errors as (path, message)."""
    if root is None:
        root = schema
    if errors is None:
        errors = []

    if schema is True:
        return errors
    if schema is False:
        errors.append((path, "schema forbids any value here"))
        return errors
    if not isinstance(schema, dict):
        raise SchemaError(f"schema at {path} must be an object or boolean")

    unsupported = set(schema) - SUPPORTED
    if unsupported:
        raise SchemaError(
            f"schema at {path} uses unsupported keyword(s): {', '.join(sorted(unsupported))}"
        )

    if "$ref" in schema:
        target = resolve_ref(schema["$ref"], root)
        validate(instance, target, root, path, errors)
        # Sibling keywords alongside $ref still apply (2020-12 semantics).
        rest = {k: v for k, v in schema.items() if k != "$ref"}
        if rest:
            validate(instance, rest, root, path, errors)
        return errors

    if schema.get("nullable") and instance is None:
        return errors

    # -- type -------------------------------------------------------------
    if "type" in schema:
        expected = schema["type"]
        expected_list = expected if isinstance(expected, list) else [expected]
        for name in expected_list:
            if name not in TYPE_CHECKS:
                raise SchemaError(f"unknown type {name!r} at {path}")
        if not any(TYPE_CHECKS[name](instance) for name in expected_list):
            errors.append(
                (path, f"expected type {' or '.join(expected_list)}, got {type_name(instance)}")
            )
            return errors  # further checks would be noise

    # -- enum / const -----------------------------------------------------
    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(json.dumps(v) for v in schema["enum"])
        errors.append((path, f"value {json.dumps(instance)} is not one of: {allowed}"))
    if "const" in schema and instance != schema["const"]:
        errors.append(
            (path, f"value must be {json.dumps(schema['const'])}, got {json.dumps(instance)}")
        )

    # -- composition ------------------------------------------------------
    if "allOf" in schema:
        for i, sub in enumerate(schema["allOf"]):
            validate(instance, sub, root, path, errors)
    if "anyOf" in schema:
        if not any(not validate(instance, s, root, path, []) for s in schema["anyOf"]):
            errors.append((path, "value does not match any of the allowed shapes (anyOf)"))
    if "oneOf" in schema:
        matched = sum(1 for s in schema["oneOf"] if not validate(instance, s, root, path, []))
        if matched != 1:
            errors.append(
                (path, f"value must match exactly one allowed shape (oneOf), matched {matched}")
            )
    if "not" in schema and not validate(instance, schema["not"], root, path, []):
        errors.append((path, "value matches a forbidden shape (not)"))

    # -- strings ----------------------------------------------------------
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append((path, f"string shorter than minLength {schema['minLength']}"))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append((path, f"string longer than maxLength {schema['maxLength']}"))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append((path, f"string does not match pattern {schema['pattern']!r}"))

    # -- numbers ----------------------------------------------------------
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append((path, f"value {instance} is below minimum {schema['minimum']}"))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append((path, f"value {instance} is above maximum {schema['maximum']}"))
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(
                (path, f"value {instance} must be greater than {schema['exclusiveMinimum']}")
            )
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(
                (path, f"value {instance} must be less than {schema['exclusiveMaximum']}")
            )

    # -- arrays -----------------------------------------------------------
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append((path, f"array has {len(instance)} items, minItems is {schema['minItems']}"))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append((path, f"array has {len(instance)} items, maxItems is {schema['maxItems']}"))
        if schema.get("uniqueItems"):
            seen = []
            for item in instance:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    errors.append((path, "array items must be unique"))
                    break
                seen.append(key)
        prefix = schema.get("prefixItems", [])
        for i, item in enumerate(instance):
            if i < len(prefix):
                validate(item, prefix[i], root, f"{path}[{i}]", errors)
            elif "items" in schema:
                validate(item, schema["items"], root, f"{path}[{i}]", errors)

    # -- objects ----------------------------------------------------------
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append((path, f"missing required property {key!r}"))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in instance:
                validate(instance[key], sub, root, f"{path}.{key}", errors)
        pattern_props = schema.get("patternProperties", {})
        for pat, sub in pattern_props.items():
            for key in instance:
                if re.search(pat, key):
                    validate(instance[key], sub, root, f"{path}.{key}", errors)
        extra = schema.get("additionalProperties")
        if extra is not None and extra is not True:
            known = set(props)
            unmatched = [
                k for k in instance
                if k not in known and not any(re.search(p, k) for p in pattern_props)
            ]
            if extra is False:
                for key in sorted(unmatched):
                    errors.append((path, f"unexpected property {key!r} (additionalProperties: false)"))
            else:
                for key in sorted(unmatched):
                    validate(instance[key], extra, root, f"{path}.{key}", errors)

    return errors


def load_json(path, what):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        die(2, f"{what} not found: {path}")
    except json.JSONDecodeError as e:
        die(2, f"{what} is not valid JSON: {path}\n  line {e.lineno}, column {e.colno}: {e.msg}")
    except OSError as e:
        die(2, f"cannot read {what}: {path}\n  {e}")


def die(code, message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def write_result(text):
    """Append the report to the rhei result file when running as a program state."""
    result_path = os.environ.get("RHEI_RESULT_PATH")
    if not result_path:
        return
    try:
        Path(result_path).parent.mkdir(parents=True, exist_ok=True)
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except OSError as e:
        print(f"warning: could not write RHEI_RESULT_PATH ({e})", file=sys.stderr)


def report(schema_path, instance_path, errors, artifact):
    header = f"## Artifact validation — `{artifact}`\n\n"
    header += f"- Instance: `{instance_path}`\n- Schema: `{schema_path}`\n"
    if not errors:
        body = header + "\n**Valid.** The artifact conforms to its schema.\n"
        print(f"✓ valid: {instance_path} conforms to {Path(schema_path).name}")
    else:
        lines = "\n".join(f"- `{p}` — {m}" for p, m in errors)
        body = header + f"\n**Invalid — {len(errors)} problem(s):**\n\n{lines}\n"
        print(f"✗ invalid: {instance_path} ({len(errors)} problem(s))")
        for p, m in errors:
            print(f"    {p}: {m}")
    write_result(body)
    return body


def main():
    parser = argparse.ArgumentParser(
        description="Validate a paper-pipeline artifact against its JSON Schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--schema", type=Path, help="Path to the schema file")
    parser.add_argument(
        "--schema-dir",
        type=Path,
        help="Directory of schemas; the schema is chosen by the instance's `artifact` field",
    )
    parser.add_argument("--instance", type=Path, help="Path to the artifact being validated")
    parser.add_argument(
        "--expect-artifact",
        help="Require the instance's `artifact` field to equal this value",
    )
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests and exit")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(self_test())

    if not args.instance:
        die(2, "--instance is required (or use --self-test)")
    if not args.schema and not args.schema_dir:
        die(2, "one of --schema or --schema-dir is required")

    instance = load_json(args.instance, "instance")

    artifact = instance.get("artifact") if isinstance(instance, dict) else None
    if args.expect_artifact and artifact != args.expect_artifact:
        msg = (
            f"artifact mismatch: expected {args.expect_artifact!r}, "
            f"file declares {artifact!r} — a wrong file is wired into this input"
        )
        write_result(f"## Artifact validation\n\n**Invalid.** {msg}\n")
        die(1, msg)

    schema_path = args.schema
    if schema_path is None:
        if not artifact:
            die(2, f"{args.instance} has no top-level `artifact` field; cannot pick a schema")
        schema_path = args.schema_dir / f"{artifact}.schema.json"
    schema = load_json(schema_path, "schema")

    try:
        errors = validate(instance, schema)
    except SchemaError as e:
        die(2, f"malformed schema {schema_path}: {e}")

    report(schema_path, args.instance, errors, artifact or "unknown")
    sys.exit(1 if errors else 0)


def self_test():
    """Built-in tests — no artifacts or network needed."""
    cases = []

    def case(name, instance, schema, expect_ok, expect_contains=None):
        cases.append((name, instance, schema, expect_ok, expect_contains))

    case("type ok", {"a": 1}, {"type": "object"}, True)
    case("type wrong", [], {"type": "object"}, False, "expected type object")
    case("required missing", {}, {"type": "object", "required": ["a"]}, False, "missing required")
    case("required present", {"a": 1}, {"type": "object", "required": ["a"]}, True)
    case("enum ok", "pdf", {"enum": ["pdf", "latex"]}, True)
    case("enum bad", "docx", {"enum": ["pdf", "latex"]}, False, "is not one of")
    case("const ok", "paper", {"const": "paper"}, True)
    case("const bad", "venue", {"const": "paper"}, False, "value must be")
    case("pattern ok", "P-001", {"type": "string", "pattern": "^P-[0-9]{3}$"}, True)
    case("pattern bad", "P-1", {"type": "string", "pattern": "^P-[0-9]{3}$"}, False, "does not match pattern")
    case("minimum ok", 0.5, {"type": "number", "minimum": 0, "maximum": 1}, True)
    case("maximum bad", 1.5, {"type": "number", "minimum": 0, "maximum": 1}, False, "above maximum")
    case("integer not bool", True, {"type": "integer"}, False, "expected type integer")
    case("minItems bad", [], {"type": "array", "minItems": 1}, False, "minItems")
    case(
        "nested item error",
        {"xs": [{"id": "a"}, {}]},
        {
            "type": "object",
            "properties": {
                "xs": {"type": "array", "items": {"type": "object", "required": ["id"]}}
            },
        },
        False,
        "$.xs[1]",
    )
    case(
        "additionalProperties false",
        {"a": 1, "b": 2},
        {"type": "object", "properties": {"a": {}}, "additionalProperties": False},
        False,
        "unexpected property 'b'",
    )
    case(
        "ref resolves",
        {"m": {"id": "x"}},
        {
            "$defs": {"M": {"type": "object", "required": ["id"]}},
            "type": "object",
            "properties": {"m": {"$ref": "#/$defs/M"}},
        },
        True,
    )
    case(
        "ref error path",
        {"m": {}},
        {
            "$defs": {"M": {"type": "object", "required": ["id"]}},
            "type": "object",
            "properties": {"m": {"$ref": "#/$defs/M"}},
        },
        False,
        "$.m",
    )
    case("nullable", None, {"type": "string", "nullable": True}, True)
    case("oneOf exactly one", "a", {"oneOf": [{"type": "string"}, {"type": "number"}]}, True)
    case(
        "oneOf none",
        [],
        {"oneOf": [{"type": "string"}, {"type": "number"}]},
        False,
        "matched 0",
    )
    case("uniqueItems", [1, 1], {"type": "array", "uniqueItems": True}, False, "must be unique")

    failed = 0
    for name, instance, schema, expect_ok, expect_contains in cases:
        try:
            errors = validate(instance, schema)
        except SchemaError as e:
            print(f"  FAIL {name}: unexpected SchemaError: {e}")
            failed += 1
            continue
        ok = not errors
        if ok != expect_ok:
            print(f"  FAIL {name}: expected {'valid' if expect_ok else 'invalid'}, got {errors}")
            failed += 1
            continue
        if expect_contains:
            blob = " ".join(f"{p} {m}" for p, m in errors)
            if expect_contains not in blob:
                print(f"  FAIL {name}: expected message containing {expect_contains!r}, got {blob!r}")
                failed += 1
                continue
        print(f"  ok   {name}")

    # An unsupported keyword must raise rather than silently under-validate.
    try:
        validate({}, {"type": "object", "dependentRequired": {"a": ["b"]}})
        print("  FAIL unsupported keyword: expected SchemaError")
        failed += 1
    except SchemaError:
        print("  ok   unsupported keyword raises")

    print(f"\n{len(cases) + 1 - failed}/{len(cases) + 1} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    main()
