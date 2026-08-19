# overall-review

Review the whole paper from several configurable personalities, in parallel.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

A personality is a **stance**, not just a model. Each one gets its own prompt and
its own target, and one state is generated per personality — so the disagreement
between them is real rather than sampling noise. Two reviewers who would accept
and reject the same paper for defensible reasons tell you far more than two runs
of the same prompt.

The default set is an academic reviewer, an industry-friendly reviewer who looks
for reasons to accept, and an industry-skeptical reviewer who rejects unless the
evidence is strong. Replace them wholesale with `--values`.

The merge step is explicitly **not** a judge: it copies each review faithfully and
preserves disagreement rather than averaging it away. Deduplication and
verification happen later, in `pc-member-review`, which needs the unmerged
originals to see how many independent reviewers raised the same point.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest |
| `venue` | string | `../venue-intake/venue/venue.json` | venue.json produced by venue-intake |
| `related_work` | string | _empty_ | related-work.json produced by related-work; optional — reviews are weaker without it but still run |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `personalities` | array | `` | Reviewer personalities. Each reviews the whole paper independently, with its own stance, from its own target. |
| `merge_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that merges the per-personality reviews into one artifact |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `import` | `import-inputs` → `completed` | `inputs-rejected` |
| `review-<personality>` (one per personality, concurrent) | `review-overall-<id>` → `completed` |
| `merge` | `merge-reviews` → `validate-overall-reviews` [→ `repair-overall-reviews` → …] → `completed` | `overall-reviews-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import` schema-checks `paper.json`, `venue.json`, and optionally
   `related-work.json` at the boundary, before any reviewer spends tokens.
2. One task per personality runs concurrently, each on its own target with its own
   stance, writing `reviews/overall/<id>.json`.
3. `merge` waits on all of them and assembles `reviews/overall-reviews.json`.

Run with `rhei run <workspace> --parallel N` to get the fan-out.

## Produces

`reviews/overall-reviews.json` (`overall-reviews`)

## Instantiate

```bash
rhei instantiate overall-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json --values personalities.yaml --output overall/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
