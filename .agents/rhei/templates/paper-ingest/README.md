# paper-ingest

Read one submission once — PDF or LaTeX — and emit the `paper.json` every other template consumes.

Part of the [paper pipeline](../../shared/README.md) — eight composable templates
that hand structured, schema-validated artifacts to each other.

**Used in:** Every flow — it is the foundation the other seven read. See [the five flows](../../shared/README.md#which-flow-do-i-run) for
copy-pasteable commands.

This is the foundation of the pipeline. Nothing else re-reads the paper.

**The PDF-vs-LaTeX choice lives here**, and only here. On the PDF path every page
is rendered to a PNG and the agent reads the images, so figures and table layouts
are described from what is actually on the page. On the LaTeX path the sources are
flattened and read directly, which keeps section structure and exact numbers but
produces no page images. Downstream templates never know which path ran — they
read the same `paper.json` either way.

Extraction does not review. A judgement smuggled into the extraction reaches every
reviewer downstream as if it were fact, so this template is prompted to be
faithful and neutral, and the review templates are prompted to be neither.

## Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `paper` (positional 1) | string | **required** | The submission — a PDF file, a LaTeX main file, or a directory containing LaTeX sources |
| `paper_id` | string | `submission` | Stable identifier used in filenames and in every downstream artifact (e.g. "submission-42") |
| `source_kind` | string | `auto` | Which ingest path to take — "auto" detects from the path, "pdf" renders and reads pages, "latex" flattens and reads the source |
| `render_dpi` | number | `150` | Resolution for per-page PNG rendering on the PDF path |
| `ingest_target` | string | `claude-code[yolo]:anthropic:claude-opus-5` | Agent target that reads the paper and writes the artifacts |
| `repair_attempts` | number | `2` | How many times the agent may repair paper.json after a schema-validation failure before the run stops for a human |
| `agent_timeout` | string | `30m` | Per-agent wall-clock timeout, e.g. "30m" or "2h" |
| `agents_json` | string | see `template.yaml` | JSON object declaring the agent programs your selectors refer to, written verbatim into .agents/rhei/settings.json. Any agent named in a selector must be declared here or in your global rhei settings, including the modes used in brackets — an undeclared agent or mode fails instantiation. Supply with --set-file agents_json=<file>. The default declares `codex`; `claude-code` and other built-ins need no declaration. |

## Per-task paths through the state machine

| Task | Path |
|---|---|
| `ingest` | `ingest` → `validate-paper` [→ `repair-paper` → `validate-paper`] → `completed` | `ingest-failed` |

The diagram lives at the top of [`states.yaml`](states.yaml).

## Flow

1. `ingest` detects the source kind (or takes the one you set), renders pages for
   a PDF, and writes `paper/full-text.md` plus `paper/paper.json`.
2. `validate-paper` — a **program**, not an agent — checks `paper.json` against
   `schemas/paper.schema.json`. Whether a file conforms to a schema is a decided
   question; letting a model answer it would defeat the point of the contract.
3. On a violation, `repair-paper` gets the validator's exact JSON-path errors and
   fixes the artifact, up to `repair_attempts` times.
4. If it still fails, `ingest-failed` parks the task for a human. Nothing
   downstream should run against an artifact that never validated.

## Produces

`paper/paper.json` (`paper`), `paper/full-text.md`

## Instantiate

```bash
rhei instantiate paper-ingest submission-42.pdf --set paper_id=submission-42 --output ingest/
```

Then `rhei run <workspace>`. Every artifact this template writes is validated
against the schemas in [`schemas/`](schemas/) before the workspace can complete;
[`examples/`](examples/) holds a well-formed instance of each.
