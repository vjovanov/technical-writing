# related-work

Deep literature sweep for what the paper must be judged against — independent of the committee.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

Deliberately blind to who is on the PC.

`pc-citation-scan` answers "whose work should I be seen to know?"; this answers
"what does this paper actually have to beat?" Conflating them produces a
bibliography optimized for politics rather than for the argument, and misses
competing work by people who happen not to be on the committee.

The sweep searches from several angles — the paper's own terms, the problem stated
independently of the paper's solution, the technique in adjacent domains, recent
work that may postdate the paper's related-work section, and the authors' own
earlier papers for self-overlap.

Every entry carries a `relation` and `cited_by_paper`. An entry that is
`closest-prior` or `competing` and **not** cited is the most valuable thing this
sweep produces.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `max_papers` | number | `20` | Cap on papers indexed |
| `download_pdfs` | boolean | `true` | Whether to download openly accessible PDFs into related/pdfs/ |
| `search_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that runs the literature sweep |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `search` | `import-inputs` → `search-literature` → `validate-related-work` [→ `repair-related-work` → …] → `completed` | `related-work-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import-inputs` brings in `paper.json`.
2. `search-literature` runs the multi-angle sweep, records the queries it used so
   the sweep can be reproduced or widened, downloads openly accessible PDFs when
   `download_pdfs` is set, and ranks at most `max_papers` entries.
3. The artifact is schema-checked, with the usual repair loop and gate.

## Produces

`related/related-work.json` (`related-work`), `related/pdfs/`

## Instantiate

```bash
rhei instantiate related-work --set paper=../ingest/paper/paper.json --output related/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
