# Rhei: PC member review — {{paper_id}}
**States:** pc-member-review

## Overview

The composed final step, for when you are the one submitting the review.

Takes every upstream artifact, merges the reviews into deduplicated addressable
points `P-xxx`, has a **different model** verify each point against the paper,
puts the surviving points in front of a human, and renders the venue's own review
form.

Inputs, all schema-checked at the boundary before anything runs:

| Artifact | From | Required |
|---|---|---|
| `paper.json` | `paper-ingest` | yes |
| `venue.json` | `venue-intake` | yes |
| `overall-reviews.json` | `overall-review` | yes |
| `section-reviews.json` | `section-review` | yes |
| `related-work.json` | `related-work` | optional |
| `pc-citations.json` | `pc-citation-scan` | optional |

Two human gates, both real:

1. **Point curation** — you see every point with its verdict and decide what
   survives. Your `human_action` overrides the verifier.
2. **Final sign-off** — you approve the outward-facing review, or send it back
   with feedback up to {{render_passes}} times.

Scores are written `[SUGGESTED]`. The review goes out under your name, so the
last judgement is yours; a model that has never had to defend a score in a PC
meeting should not be making it silently.

## Outputs

- `review/review-points.json` — verified points, schema-validated
- `review/submission-{{paper_id}}.txt` — the file to paste into the review system
- `review/final-review-{{paper_id}}.md` — the long form, keeping `[P-xxx]`
  traceability back to the verified points
