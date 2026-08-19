# Rhei: Related work — {{paper_id}}
**States:** related-work

## Overview

Finds the literature this submission has to be judged against, at most
{{max_papers}} entries{% if download_pdfs %}, downloading openly accessible PDFs into
`related/pdfs/`{% endif %}. Writes `related/related-work.json`, validated against
`schemas/related-work.schema.json`.

Deliberately independent of the program committee. `pc-citation-scan` answers
"whose work should I be seen to know?"; this answers "what does this paper
actually have to beat?" Conflating the two produces a bibliography optimized for
politics rather than for the argument, and misses competing work by people who
happen not to be on the committee.

Every entry carries a `relation` — `closest-prior`, `competing`, `seminal`,
`recent`, `self-overlap`, or `background` — and `cited_by_paper`. An entry that
is `closest-prior` or `competing` and *not* cited is the most valuable thing
this sweep can find.

## Consumed by

`related/related-work.json` is an optional input of `overall-review`,
`section-review`, and `pc-member-review`.
