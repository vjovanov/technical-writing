# venue-intake

Resolve a venue reference into `venue.json` and the full program committee.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

Two artifacts from one reference — a URL, a local file, or a bare venue name.

`venue.json` records what the venue selects for and, critically,
`review_form.fields[]`: every field a reviewer actually fills in, with its type
and scale. That is what `pc-member-review` renders the final review against, so a
field missed here becomes a missing section of the submitted review.

An offline review form (a HotCRP `==+==` text form) is kept **byte-for-byte** in
`venue/review-form.txt` and reproduced verbatim at the end of the pipeline. Its
markers are parsed by the submission system; paraphrasing it corrupts the
submission.

The two tasks are independent on purpose: a venue that publishes no committee
roster should still yield a usable `venue.json`.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `conference` (positional 1) | string | **required** | Venue reference — the conference website URL (preferred), a local file with venue information, or just the venue name |
| `guidelines` | string | _empty_ | Reviewer guidelines verbatim (--set-file guidelines=<file>); harvested from the venue when omitted |
| `review_form` | string | _empty_ | Offline review form verbatim, e.g. a HotCRP "==+==" text form (--set-file review_form=<file>); harvested from the venue when omitted |
| `harvest_pc` | boolean | `true` | Whether to harvest the program committee roster; set false when the venue publishes no PC or you do not need reviewer matching |
| `intake_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that resolves the venue and harvests the committee |
| `repair_attempts` | number | `2` | How many times the agent may repair an artifact after a schema-validation failure before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `venue` | `resolve-venue` → `validate-venue` [→ `repair-venue` → `validate-venue`] → `completed` | `venue-failed` |
| `committee` | `harvest-pc` → `validate-pc` [→ `repair-pc` → `validate-pc`] → `completed` | `pc-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `resolve-venue` reads the reference, writes `venue/guidelines.md` and
   `venue/review-form.txt` verbatim, and writes the structured `venue.json`.
   Content you supplied with `--set-file` is left untouched.
2. `harvest-pc` collects the committee roster, slugifying each name into a stable
   `id` that every downstream artifact references. It sets `complete: false` and
   says why if the roster could not be fully harvested — a silent gap would read
   as a confident negative during reviewer matching.
3. Each artifact is schema-checked by a program state, with a bounded repair loop
   and a human gate behind it.

## Produces

`venue/venue.json` (`venue`), `venue/program-committee.json` (`program-committee`)

## Instantiate

```bash
rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA --output venue/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
