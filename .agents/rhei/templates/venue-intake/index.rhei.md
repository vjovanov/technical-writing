# Rhei: Venue intake — {{conference}}
**States:** venue-intake

## Overview

Turns the venue reference `{{conference}}` — a URL, a local file, or a bare name —
into two schema-validated artifacts:

- `venue/venue.json` — scope, selection criteria, dates, review process, and the
  review form a reviewer must fill in, field by field.
- `venue/program-committee.json` — the full committee roster with roles,
  affiliations, and topics.{% if not harvest_pc %} *(PC harvesting is disabled for this instantiation.)*{% endif %}

Verbatim material the venue publishes is kept as-is beside the JSON:
`venue/guidelines.md` and `venue/review-form.txt`. An offline review form is
reproduced byte-for-byte in the final submission later in the pipeline, so it is
never paraphrased here.

## Consumed by

`venue/venue.json` is the `venue` input of `overall-review`, `section-review`,
and `pc-member-review`. `venue/program-committee.json` is the `program_committee`
input of `reviewer-match`.
