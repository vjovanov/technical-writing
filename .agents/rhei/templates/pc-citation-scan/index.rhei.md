# Rhei: PC citation scan — {{paper_id}}
**States:** pc-citation-scan

## Overview

For every committee member likely to review this paper, finds the work of theirs
that the paper ought to be engaging with — and checks whether it is already
cited.

Scans members in bands {% for b in bands %}`{{ b }}`{% if not loop.last %}, {% endif %}{% endfor %},
at most {{max_papers_per_member}} papers each. Writes
`citations/pc-citations.json`, validated against
`schemas/pc-citations.schema.json`.

This is reconnaissance, not flattery. A reviewer who finds their directly
relevant prior work uncited reads that as carelessness about the literature;
one who finds it cited gratuitously reads that as padding. Each entry therefore
records *why* the paper matters — `relevance` — and a `citation_priority` of
`must`, `should`, or `optional`, so the distinction stays visible.

## Consumed by

`citations/pc-citations.json` is an optional input of `pc-member-review`, and is
useful on its own when you are the author deciding what to cite before
submitting.
