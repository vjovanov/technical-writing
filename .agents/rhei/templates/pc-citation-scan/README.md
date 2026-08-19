# pc-citation-scan

Find each likely reviewer's own work the paper should engage with, and whether it is cited.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

Reconnaissance, not flattery.

For each member in the bands you select, this finds their publications that
genuinely bear on the submission and checks whether the paper already cites them.
Each entry records *why* it matters and a `citation_priority` of `must`, `should`,
or `optional`.

The distinction is the whole value. A reviewer who finds their directly relevant
prior work uncited reads that as carelessness about the literature; one who finds
it cited gratuitously reads that as padding. The template is prompted not to
inflate priority to flatter a likely reviewer.

Most useful when you are the **author** deciding what to cite before submitting.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` | string | `../paper-ingest/paper/paper.json` | paper.json produced by paper-ingest |
| `reviewer_matches` | string | `../reviewer-match/matches/reviewer-matches.json` | reviewer-matches.json produced by reviewer-match |
| `paper_id` | string | `submission` | Stable identifier, matching the one in paper.json |
| `bibliography` | string | _empty_ | The paper's .bib file, used to decide what is already cited; when empty, citations are judged from the full text alone |
| `bands` | array | `["high", "medium"]` | Which reviewer-match bands to scan; scanning low-band members is usually wasted effort |
| `max_papers_per_member` | number | `5` | Cap on papers indexed per committee member |
| `scan_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that scans each member's publication record |
| `repair_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that repairs schema violations |
| `repair_attempts` | number | `2` | How many times the agent may repair the artifact before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `scan` | `import-inputs` → `scan-citations` → `validate-pc-citations` [→ `repair-pc-citations` → …] → `completed` | `pc-citations-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `import-inputs` brings in `paper.json` and `reviewer-matches.json`.
2. `scan-citations` selects members whose `band` is in `bands`, skips those with
   a recorded conflict, and indexes up to `max_papers_per_member` works each.
3. Citation status is decided from your `.bib` when you supply one, otherwise
   from the paper's full text — and says so when it cannot tell.
4. The artifact is schema-checked, with the usual repair loop and gate.

## Produces

`citations/pc-citations.json` (`pc-citations`)

## Instantiate

```bash
rhei instantiate pc-citation-scan --set paper=../ingest/paper/paper.json \
  --set reviewer_matches=../matches/matches/reviewer-matches.json \
  --set bibliography=../paper/references.bib --output citations/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
