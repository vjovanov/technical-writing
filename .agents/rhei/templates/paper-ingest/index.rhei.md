# Rhei: Paper ingest — {{paper_id}}
**States:** paper-ingest

## Overview

Reads the submission at `{{paper}}` exactly once and turns it into the two
artifacts the rest of the paper pipeline is built on:

- `paper/full-text.md` — a faithful, neutral full-text extraction.
- `paper/paper.json` — the machine-readable reading: section map, claimed
  contributions, falsifiable claims, and a topic profile. Validated against
  `schemas/paper.schema.json` before this workspace can complete.

Ingest mode is `{{source_kind}}`. On the PDF path every page is first rendered
to a PNG at {{render_dpi}} DPI so the agent reads the paper as laid out, figures
included. On the LaTeX path the sources are flattened and read directly, which
preserves section structure and exact numbers but produces no page images.

Nothing here judges the paper. Extraction and review are separate jobs, and
mixing them biases every reviewer downstream.

## Consumed by

`paper/paper.json` is the `paper` input of `reviewer-match`, `pc-citation-scan`,
`related-work`, `overall-review`, `section-review`, and `pc-member-review`.
