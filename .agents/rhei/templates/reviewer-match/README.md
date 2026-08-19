# reviewer-match

Estimate which committee members are likely to review the paper, with evidence.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

**Used in:** Pre-submission recon only. A reviewer already knows they were assigned the paper. See [the five flows](../../shared/README.md#which-flow-do-i-run) for
copy-pasteable commands.

Answers "who will probably read this?" — with grounds, not vibes.

Every match carries a `likelihood` in [0,1], a `band`, a written `rationale`, and
`evidence[]` naming what it rests on: a specific paper of theirs, a stated PC
topic, prior service on this venue's committee. The schema requires the rationale
because a number without one is a guess wearing a decimal point.

Conflicts are recorded and drop the band: a member sharing an affiliation with an
author will not be assigned the paper however well their topics match.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest |
| `program_committee` | string | `../venue-intake/venue/program-committee.json` | program-committee.json produced by venue-intake |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `author_names` | array | _empty list_ | Author names used to detect conflicts of interest; leave empty for a double-blind submission you are reviewing rather than writing |
| `match_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that researches committee members and estimates likelihood |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `match` | `import-inputs` → `match-reviewers` → `validate-reviewer-matches` [→ `repair-reviewer-matches` → …] → `completed` | `reviewer-matches-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import-inputs` copies `paper.json` and `program-committee.json` in, refusing
   anything missing, wrong, or malformed — before any research is done.
2. `match-reviewers` triages the roster, researches the plausible members, and
   records likelihood with concrete evidence. Obvious non-matches get a low band
   and one line; effort goes where it changes the answer.
3. The artifact is schema-checked, with the usual repair loop and gate.

Supply `author_names` to enable conflict detection. Without it the template says
so in `method` rather than silently reporting no conflicts.

## Produces

`matches/reviewer-matches.json` (`reviewer-matches`)

## Instantiate

```bash
rhei instantiate reviewer-match --set paper=../ingest/paper/paper.json \
  --set program_committee=../venue/venue/program-committee.json --output matches/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
