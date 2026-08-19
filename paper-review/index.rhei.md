# Rhei: Paper Review — {{conference}}
**States:** paper-review

## Overview
Multi-model review of the submission at `{{paper}}` for the venue
referenced as `{{conference}}` (a website URL, a local file, or a name —
resolved into `inputs/venue.md` by the venue task).

The instantiated workspace is the per-paper folder: page screenshots, the
canonical full-text extraction, downloaded related work, per-model reviews,
verified review points, and the final submission-ready review all live here.

Reviewer models (each summarizes the paper and reviews every topic
independently):
{%- for r in reviewers %}
- `{{ r.selector }}` — {{ r.label }}
{%- endfor %}

Aggregator: `{{aggregator_target}}` · Verifier: `{{verifier_target}}` ·
Utility (ingest / search / planning): `{{utility_target}}`

Flow:

1. `venue` resolves the venue reference: it fetches the conference website
   (or reads the given file), writes `inputs/venue.md`, and fills
   `inputs/guidelines.md` / `inputs/review-form.md` from the venue's
   published material wherever the user did not supply them.
2. `ingest` reads the paper once — a PDF is first rendered page-by-page into
   `paper/pages/` — and writes `paper/full-text.md` plus `paper/digest.md`
   (section map, contributions, key claims). Every later task reads these
   artifacts instead of re-reading the PDF.
3. `related-work` searches the literature, downloads up to {{max_related}}
   openly accessible papers into `related/pdfs/`, and writes
   `related/index.md`.
4. **Human gate (intake):** the `coordinate` task starts gated. Approve or
   fix the digest's section map, the related-work index, and the venue
   files under `inputs/`, then transition the task to `plan-review`.
5. The coordinator appends one `review-<slug>` task per `core` section, plus
   `review-evaluation`, `review-related-work`, and the `aggregate` task.
6. `summarize` fans out across all reviewer models — each writes an overall
   summary focused on contribution to the community. Each `review-topic`
   task fans out the same way for its topic; topic tasks run concurrently.
7. The `aggregate` task walks the tail of the pipeline:
   `aggregate-points` (aggregator merges everything into addressable points
   `P-xxx`) → `verify-points` (verifier confirms / weakens / rejects each
   point) → **human gate (points curation)** → `render-report` (fills the
   review form; scores marked `[SUGGESTED]`) → **human gate (final
   sign-off)**, which either completes the review or loops back to
   `render-report` with feedback from `review/human-feedback.md`.

## Notes

- Rejected points never reach the report; weakened points use the verifier's
  revised statement; human edits at the curation gate override the verifier.
- `review/submission-<paper_id>.txt` (full) and
  `review/submission-<paper_id>-short.txt` (concise, human-facing) are the
  files to submit; `review/final-review-<paper_id>.md` keeps point
  traceability (`[P-xxx]`) and `[SUGGESTED]` score markers.
- The workspace is "living": the coordinator appends task files under
  `tasks/` during the run. `rhei reset` clears state but does not delete
  dynamically appended task files.
- `inputs/guidelines.md` and `inputs/review-form.md` hold user-supplied
  content when given at instantiation; otherwise the venue task fills them
  from the venue website (offline review forms — e.g. HotCRP `==+==` text —
  are kept verbatim and reproduced verbatim in `review/submission-<paper_id>.txt`).
