{% for p in personalities %}
### Task review-{{ p.id }}: Overall review — {{ p.label }}
**State:** review-overall-{{ p.id }}
**Prior:** Task import

Review the whole of `{{paper_id}}` as **{{ p.label }}**, writing your review to
`reviews/overall/{{ p.id }}.json`.

{% endfor %}
