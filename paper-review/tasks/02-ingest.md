### Task ingest: Ingest the paper
**State:** ingest

Read the submission at `{{paper}}` once. If it is a PDF, first render every
page into `paper/pages/`. Produce `paper/full-text.md` (faithful full-text
extraction, including figure and table descriptions) and `paper/digest.md`
(section map with core/boilerplate marks, claimed contributions, key
claims) as the canonical reading every later task builds on.
