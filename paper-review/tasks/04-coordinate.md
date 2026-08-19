### Task coordinate: Approve intake and plan the review
**State:** intake-review
**Prior:** Task venue, Task ingest, Task related-work

Starts as a human gate: approve or fix `paper/digest.md` (its `core` marks
control which review tasks are spawned), `related/index.md`, and the venue
files under `inputs/` (venue notes, guidelines, review form), then
transition to `plan-review`. The coordinator then appends one
`review-<slug>` task per core section, the `review-evaluation` and
`review-related-work` tasks, and the `aggregate` task that waits on all of
them plus `summarize`.
