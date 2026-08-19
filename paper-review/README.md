# paper-review

Multi-model conference paper review. One instantiation = one paper: the
instantiated workspace is the per-paper folder holding page screenshots, the
canonical full-text extraction, downloaded related work, per-model reviews,
aggregated and verified review points, and the final submission-ready
review. Two reviewer models (Codex on GPT 5.6 Sol high and Claude Opus 4.8
by default) independently summarize the paper and review every topic; the
best model (Fable) aggregates their output into addressable points; a
configurable verifier (Opus 4.8 by default) checks every point against the
paper; a human curates the points and signs off on the outward-facing
review.

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `paper` | path | required, positional 1 | The submission — a PDF file, or a LaTeX main file / source directory |
| `paper_id` | string | derived from paper filename | Identifier put into output filenames (e.g. the paper number, `42`); when omitted, derived from the paper filename stem (e.g. `submission-42`) |
| `conference` | string | required | Venue reference: the conference website URL (preferred), a local file with venue info, or just the venue name |
| `guidelines` | string | `""` | Optional reviewer guidelines (`--set-file guidelines=<file>`); harvested from the venue website when omitted |
| `review_form` | string | `""` | Optional verbatim offline-review form, e.g. a HotCRP `==+==` text form (`--set-file review_form=<file>`); harvested from the venue or defaulted when omitted |
| `reviewers` | array | Codex (GPT 5.6 Sol, high) + Claude (Opus 4.8) | `{id, label, selector}` reviewer models (override with `--values`) |
| `aggregator_target` | string | `claude-code[yolo]:anthropic:claude-opus-4-8` | Merges reviews into points and renders the report |
| `verifier_target` | string | `claude-code[yolo]:anthropic:claude-opus-4-8` | Verifies every point against the paper |
| `utility_target` | string | `claude-code[yolo]:anthropic:claude-opus-4-8` | Ingest, related-work search, review planning |
| `max_related` | number | `10` | Cap on related papers indexed/downloaded |

## Per-task paths through the state machine

See the diagram at the top of [states.yaml](states.yaml).

| Task | Path |
|---|---|
| `venue` | `ingest-venue → completed` |
| `ingest` | `ingest → completed` |
| `related-work` | `search-related → completed` |
| `coordinate` | `intake-review [gate] → plan-review → completed` |
| `summarize` | `summarize (all reviewers) → completed` |
| `review-<slug>` / `review-evaluation` / `review-related-work` (spawned) | `review-topic (all reviewers, concurrent) → completed` |
| `aggregate` (spawned) | `aggregate-points → verify-points → points-review [gate] → render-report → final-signoff [gate] (→ render-report)* → completed` |

## Flow

0. `venue` resolves the venue reference — URL fetched, file read, or name
   searched — into `inputs/venue.md`, and fills `inputs/guidelines.md` /
   `inputs/review-form.md` from the venue's published material wherever the
   user did not supply them (marker `<!-- venue-intake: fill -->`). An
   offline review form (HotCRP `==+==` text) is kept verbatim, and
   `render-report` later reproduces it verbatim in `review/submission-<paper_id>.txt`,
   filling only the response areas.
1. `ingest` reads the paper once — PDFs are first rendered page-by-page into
   `paper/pages/` — and writes `paper/full-text.md` plus `paper/digest.md`
   (section map with `core`/`boilerplate` marks, contributions `C-x`, key
   claims `K-x`). Downstream agents read these artifacts instead of
   re-reading the PDF.
2. `related-work` searches the literature and downloads openly accessible
   PDFs into `related/pdfs/`, writing the ranked `related/index.md`.
3. **Human gate 1 (intake):** approve or fix the digest's section map and
   the related-work index, then transition `coordinate` to `plan-review`.
4. The coordinator appends one `review-<slug>` task per `core` section plus
   `review-evaluation`, `review-related-work`, and the `aggregate` task —
   the review topics are decided by what the paper actually contains, not at
   instantiation time.
5. Every reviewer model independently writes the overall summary
   (`reviews/summary/<target>.md`) and per-topic findings
   (`reviews/findings/<task>-<target>.md`, ids `F-<task>-NN`).
6. The aggregator merges everything into addressable points `P-xxx`
   (`points/points.md`) and a consolidated summary (`points/summary.md`).
7. The verifier classifies every point `confirmed`/`weakened`/`rejected`
   with evidence (`points/verification.md`); rejected points never reach the
   report.
8. **Human gate 2 (points curation):** strike, sharpen, or add points — the
   files as edited are ground truth.
9. `render-report` fills every review-form field; numeric/score fields get a
   justified suggestion marked `[SUGGESTED]`. It writes
   `review/final-review-<paper_id>.md` (traceable, with `[P-xxx]` markers),
   `review/submission-<paper_id>.txt` (submission syntax, clean, full), and
   `review/submission-<paper_id>-short.txt` — a shortened, human-facing rendering with
   the same scaffolding and scores: majors/all-reviewer points kept with
   their specifics, minors folded into one paragraph, prose rewritten to
   read like a person (no wall-to-wall bold, no em-dash pile-ups, at most
   four rebuttal questions), and the AI-assisted-then-human-verified note
   in any PC-only field.
10. **Human gate 3 (final sign-off):** confirm/override scores (mirrored in
    both submission files) and approve whichever rendering you upload —
    `submission-<paper_id>.txt` (full) or `submission-<paper_id>-short.txt` (concise) — or write
    `review/human-feedback.md` and loop back to `render-report` (loop
    budget 3).

## Instantiate

Minimal — everything venue-related harvested from the conference website:

```bash
rhei instantiate paper-review ~/papers/submission-42.pdf \
  --set conference="https://conf.researchr.org/home/oopsla-2027" \
  --output reviews/submission-42/
```

With the venue's offline review form supplied verbatim (recommended when
you have it — it carries the exact fields, help text, and score enums):

```bash
rhei instantiate paper-review ~/papers/submission-42.pdf \
  --set conference="https://conf.researchr.org/home/oopsla-2027" \
  --set-file review_form=~/papers/offline-review-form.txt \
  --output reviews/submission-42/
```

Override the reviewer panel or verifier with a values file:

```bash
rhei instantiate paper-review /path/to/main.tex \
  --values reviewers.yaml \
  --set conference="OOPSLA 2027" \
  --set-file guidelines=guidelines.md \
  --output reviews/submission-43/
```

## Example

This is a user-global template (`~/.agents/rhei/templates/paper-review/`),
so no example is checked into a repository. To smoke-test after editing,
instantiate with a scratch PDF and run:

```bash
rhei instantiate paper-review /tmp/paper.pdf --set conference="X 2027" \
  --output /tmp/pr-test
rhei validate /tmp/pr-test && rhei run /tmp/pr-test --dry-run
```

Note: the `paper` input is a `path`, so its absolute path is baked into the
rendered workspace — instantiate on the machine where the review will run.
The bundled `settings.json` declares the `codex` agent (with the `high`
reasoning mode) and a 30-minute agent timeout; `claude-code` and `gemini`
selectors resolve from built-in/global agent settings.
