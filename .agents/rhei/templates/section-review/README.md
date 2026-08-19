# section-review

Chapter-by-chapter review — one task per core section per personality, spawned at run time.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

**Used in:** Reviewer, mock review, section deep dive. See [the five flows](../../shared/README.md#which-flow-do-i-run) for
copy-pasteable commands.

How many sections a paper has is not known until it has been read, so the review
tasks are **spawned at run time**: the coordinator reads the section map in
`paper.json` and appends one task file per `core` section per personality, plus
the merge task that waits on all of them.

Task count is (core sections × personalities), so the `core`/`boilerplate` marks
in `paper.json` directly control what this costs. Re-mark them there before
running if the split is wrong.

Section review catches what a whole-paper pass misses. An imprecise definition in
Section 2 that everything later depends on is easy to skim past when reading for
an overall verdict, and hard to miss when Section 2 is the only thing in front of
you.

Every finding must carry a `suggestion`. That is not politeness — a finding
without a concrete improvement path is a complaint the authors cannot act on.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest; its sections[] marked `core` decide what gets reviewed |
| `venue` | string | `../venue-intake/venue/venue.json` | venue.json produced by venue-intake |
| `related_work` | string | `../related-work/related/related-work.json` | related-work.json produced by related-work. Optional — if you ran that template into a sibling directory it is picked up automatically, and if you did not, the review still runs without it. |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `personalities` | array | `` | Reviewer personalities. Every core section is reviewed once per personality, so the task count is (core sections x personalities). |
| `coordinator_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that reads the section map and spawns the per-section review tasks |
| `merge_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that merges the per-section findings into one artifact |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `coordinate` | `import-inputs` → `plan-sections` → `completed` | `inputs-rejected` |
| `review-<section>-<personality>` (spawned, concurrent) | `review-section-<id>` → `completed` |
| `merge` (spawned) | `merge-sections` → `validate-section-reviews` [→ `repair-section-reviews` → …] → `completed` | `section-reviews-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import-inputs` schema-checks the upstream artifacts at the boundary.
2. `plan-sections` reads `sections[]`, and for every entry marked `core` appends
   one task file per personality with concrete, section-specific questions — plus
   `tasks/90-merge.md` whose `**Prior:**` names every spawned task.
3. The spawned tasks run concurrently, each writing findings for one section.
4. `merge` assembles them without deduplicating: two personalities independently
   finding the same problem is evidence, and the next template needs to see both.

## Produces

`reviews/section-reviews.json` (`section-reviews`)

## Instantiate

```bash
rhei instantiate section-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json --output sections/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
