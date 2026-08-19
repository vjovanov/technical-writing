# pc-member-review

The composed final step — verified review points and the submission-ready review, behind two human gates.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

For when you are the one submitting the review. This is what the old monolithic
`paper-review` template did, now assembled from artifacts the other templates
produce.

**The verifier runs on a different model from the aggregator by default.** A model
checking points it wrote itself is not an independent check, and the entire
purpose of the verify stage is to kill plausible-but-wrong findings before a human
spends attention on them. A reviewer claiming something is missing when it is on
page 7 wastes the authors' rebuttal and embarrasses the reviewer.

Verdicts are `confirmed`, `weakened` (partly right — the corrected claim goes in
`verified_statement`), or `rejected`. Rejected points never reach the report.

Scores are written `[SUGGESTED]`. The review goes out under your name, so the last
judgement is yours; a model that has never had to defend a score in a PC meeting
should not be making it silently.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest |
| `venue` | string | `../venue-intake/venue/venue.json` | venue.json produced by venue-intake; its review_form drives the final output |
| `overall_reviews` | string | `../overall-review/reviews/overall-reviews.json` | overall-reviews.json produced by overall-review |
| `section_reviews` | string | `../section-review/reviews/section-reviews.json` | section-reviews.json produced by section-review |
| `related_work` | string | _empty_ | related-work.json produced by related-work; optional |
| `pc_citations` | string | _empty_ | pc-citations.json produced by pc-citation-scan; optional, and normally only useful to an author rather than a reviewer |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `aggregator_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that merges reviews into addressable points and renders the report |
| `verifier_target` | string | `codex[high]:openai:gpt-5.6-sol` | Agent target that independently checks every point against the paper. Use a different model from the aggregator — a model checking its own output is not an independent check. |
| `render_passes` | number | `3` | How many times the report may be sent back for revision at the final gate |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `review` | `import-inputs` → `aggregate-points` → `verify-points` → `validate-review-points` [→ `repair-review-points` → …] → `points-review` [gate] → `render-report` → `final-signoff` [gate] (→ `render-report`)* → `completed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import-inputs` schema-checks **every** upstream artifact at the boundary —
   four required, two optional. A stale or wrong file is caught here, for the cost
   of one program invocation.
2. `aggregate-points` merges the overall and section reviews into deduplicated
   points `P-001`, `P-002`, …, each listing every review that raised it.
3. `verify-points` checks each point against the paper itself, on a different
   target, and assigns a verdict.
4. **Human gate — point curation.** You set `human_action` per point; it overrides
   the verifier in both directions.
5. `render-report` fills the venue's own form, reproducing a verbatim offline form
   byte-for-byte and filling only the response areas.
6. **Human gate — final sign-off.** Approve, or write `review/human-feedback.md`
   and send it back, up to `render_passes` times.

## Produces

`review/review-points.json` (`review-points`), `review/submission-<id>.txt`, `review/final-review-<id>.md`

## Instantiate

```bash
rhei instantiate pc-member-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json \
  --set overall_reviews=../overall/reviews/overall-reviews.json \
  --set section_reviews=../sections/reviews/section-reviews.json --output review/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
