# Rhei: Reviewer match — {{paper_id}}
**States:** reviewer-match

## Overview

Estimates, for every member of the program committee, how likely they are to be
assigned this paper — and says why.

Reads `{{paper}}` for the paper's topic profile and `{{program_committee}}` for
the roster, then researches each plausible member's recent work and stated
interests. Writes `matches/reviewer-matches.json`, validated against
`schemas/reviewer-matches.schema.json`.

Each match carries a `likelihood` in [0,1], a coarse `band`, a written
`rationale`, and `evidence[]` naming the concrete grounds — their papers, their
stated topics, their prior PC service. A number without evidence is a guess
wearing a decimal point, so the schema requires the rationale.

Conflicts are recorded too: a member who cannot review the paper is not a likely
reviewer no matter how well their topics match.

## Consumed by

`matches/reviewer-matches.json` is the `reviewer_matches` input of
`pc-citation-scan`, which scans the high- and medium-band members' own work for
citations this paper should be engaging with.
