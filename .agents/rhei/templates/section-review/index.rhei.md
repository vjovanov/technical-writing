# Rhei: Section review — {{paper_id}}
**States:** section-review

## Overview

Reviews the paper one section at a time. How many sections there are is not known
until the paper is read, so the review tasks are **spawned at run time**: the
coordinator reads the section map in `paper.json` and appends one task per
`core` section per personality.

Personalities for this instantiation:
{% for p in personalities %}
- **{{ p.label }}** (`{{ p.id }}`) — `{{ p.selector }}`
{%- endfor %}

Task count is (core sections × {{ personalities | length }} personalities), so
the `core`/`boilerplate` marks in `paper.json` directly control what this costs.
Re-mark them there before running if the split is wrong.

Section review catches what a whole-paper pass misses: an imprecise definition in
Section 2 that everything later depends on is easy to skim past when reading for
an overall verdict, and hard to miss when Section 2 is the only thing in front
of you.

Results merge into `reviews/section-reviews.json`, validated against
`schemas/section-reviews.schema.json`.

## Consumed by

`reviews/section-reviews.json` is the `section_reviews` input of
`pc-member-review`.
