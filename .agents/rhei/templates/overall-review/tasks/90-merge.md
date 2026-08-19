### Task merge: Merge the overall reviews
**State:** merge-reviews
**Prior:** {% for p in personalities %}Task review-{{ p.id }}{% if not loop.last %}, {% endif %}{% endfor %}

Merge every per-personality review into the single schema-validated
`reviews/overall-reviews.json`, preserving disagreement rather than averaging it.
