# Rhei: Overall review — {{paper_id}}
**States:** overall-review

## Overview

Reviews the whole paper once per configured personality, in parallel, then merges
the results into `reviews/overall-reviews.json`, validated against
`schemas/overall-reviews.schema.json`.

Personalities for this instantiation:
{% for p in personalities %}
- **{{ p.label }}** (`{{ p.id }}`) — `{{ p.selector }}`
{%- endfor %}

Each personality is a *stance*, not just a model: it gets its own prompt, so the
disagreement between them is real rather than sampling noise. Two reviewers who
would accept and reject the same paper for defensible reasons tell you far more
than two runs of the same prompt. The merge preserves the disagreement instead
of averaging it away.

## Consumed by

`reviews/overall-reviews.json` is the `overall_reviews` input of
`pc-member-review`.
