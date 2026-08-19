#!/usr/bin/env python3
"""
Emit the standard schema-validation machinery for one pipeline artifact.

Every paper-pipeline template ends the same way: an agent writes a structured
artifact, a program state checks it against its schema, a bounded repair loop
gives the agent a chance to fix violations, and an exhausted loop parks the task
on a human gate. Hand-writing that four-state block per template invites drift
between templates, which is exactly what a shared contract is supposed to
prevent — so it is generated from one definition instead.

Usage
    gen_validation_states.py states  <artifact> <path> [--target VAR] [--label L]
    gen_validation_states.py transitions <artifact>
    gen_validation_states.py profile-states <artifact>

`artifact` is the schema/`artifact` field name (e.g. `reviewer-matches`).
`path`     is where the artifact lives in the workspace.
The emitted YAML carries `{{...}}` instantiation placeholders untouched.
"""

import argparse
import sys

STATES = '''\
  validate-{slug}:
    description: Check {file} against its schema. Deterministic — a program, not an agent.
    program: "python3 scripts/validate_artifact.py --schema-dir schemas --instance {path} --expect-artifact {artifact}"
    program_timeout: 2m
    visits: {{{{repair_attempts}}}}
    inputs:
      - name: {slug}
        path: {path}

  repair-{slug}:
    description: The agent fixes the schema violations the validator reported in {file}.
    target: {{{{{target}}}}}
    visits: {{{{repair_attempts}}}}
    inputs:
      - name: {slug}
        path: {path}
    personality: |
      You are correcting a structured artifact that failed its schema contract.
      Fix the artifact to match the schema. Never weaken the schema, and never
      invent content to satisfy a required field — a fabricated value passes
      validation and then misleads every template downstream.
    instructions: |
      Repair pass {{visit_count}} of {{visits}} for Task {{task_id}}: {{task_title}}.

      `{{input.{slug}.path}}` failed validation against
      `schemas/{artifact}.schema.json`. The validator wrote every problem, each
      with its JSON path, into this task's result file. Read it, read the
      schema, and fix each one.

      The schemas are closed (`additionalProperties: false`), so an unexpected
      property must be removed rather than renamed. Ids constrained by a
      pattern must match it exactly.

      Transition to `validate-{slug}` when the artifact is corrected.

  {slug}-failed:
    description: Human gate — {file} still fails its schema after every repair attempt.
    gating: true
    final: true
    inputs:
      - name: {slug}
        path: {path}
    instructions: |
      {label} could not be made schema-valid for Task {{task_id}} within
      {{{{repair_attempts}}}} repair attempts.

      Read this task's result file for the outstanding violations, then fix
      `{path}` by hand and re-check it:

        python3 scripts/validate_artifact.py --schema-dir schemas \\
          --instance {path} --expect-artifact {artifact}

      Nothing downstream should consume this artifact until it validates.
'''

TRANSITIONS = '''\
  - from: validate-{slug}
    to: completed
    description: The artifact conforms to its schema.
    exit_code: 0

  - from: validate-{slug}
    to: repair-{slug}
    description: The artifact violates its schema and repair attempts remain.
    exit_code: nonzero
    condition: visitCount < visits

  - from: validate-{slug}
    to: {slug}-failed
    description: The artifact still violates its schema after every repair attempt.
    exit_code: nonzero
    condition: visitCount >= visits

  - from: repair-{slug}
    to: validate-{slug}
    description: The agent corrected the artifact; re-check it.
'''

PROFILE_STATES = '''\
      - validate-{slug}
      - repair-{slug}
      - {slug}-failed
'''


def slug_of(artifact):
    return artifact


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["states", "transitions", "profile-states"])
    ap.add_argument("artifact")
    ap.add_argument("path", nargs="?")
    ap.add_argument("--target", default="repair_target", help="Instantiation variable holding the repair agent target")
    ap.add_argument("--label", default=None, help="Human-readable artifact name for the gate message")
    args = ap.parse_args()

    slug = slug_of(args.artifact)
    label = args.label or args.artifact.replace("-", " ").capitalize()

    if args.what == "transitions":
        sys.stdout.write(TRANSITIONS.format(slug=slug))
        return
    if args.what == "profile-states":
        sys.stdout.write(PROFILE_STATES.format(slug=slug))
        return

    if not args.path:
        ap.error("states requires the artifact path")
    sys.stdout.write(
        STATES.format(
            slug=slug,
            artifact=args.artifact,
            path=args.path,
            file=args.path.rsplit("/", 1)[-1],
            target=args.target,
            label=label,
        )
    )


if __name__ == "__main__":
    main()
