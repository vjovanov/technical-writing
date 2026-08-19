# The paper pipeline

**Eight composable rhei templates that hand each other schema-validated
artifacts.** Run one, run a few, or run all of them; the contract between them is
a set of JSON Schemas, enforced at every boundary.

Discovered automatically by `rhei templates` and `rhei instantiate <name>` from
anywhere inside this repository — they live in `.agents/rhei/templates/`, which
is where rhei looks for project templates.

---

## The eight templates

| Template | Answers | Produces |
|---|---|---|
| [`paper-ingest`](../templates/paper-ingest/) | What does this paper actually say? | `paper` |
| [`venue-intake`](../templates/venue-intake/) | What does this venue select for, and who is on the committee? | `venue`, `program-committee` |
| [`reviewer-match`](../templates/reviewer-match/) | Who is likely to review it? | `reviewer-matches` |
| [`pc-citation-scan`](../templates/pc-citation-scan/) | Whose work should this paper be engaging with? | `pc-citations` |
| [`related-work`](../templates/related-work/) | What does it have to beat? | `related-work` |
| [`overall-review`](../templates/overall-review/) | What do reviewers of different stances make of it? | `overall-reviews` |
| [`section-review`](../templates/section-review/) | What is wrong section by section? | `section-reviews` |
| [`pc-member-review`](../templates/pc-member-review/) | What review do I submit? | `review-points`, the submission file |

`paper-ingest` is not one of the six steps you might have expected. It exists
because "run the review on a PDF or on LaTeX" is an *ingest* concern, not a review
concern: it is settled once, there, and the six downstream templates read the same
`paper.json` either way and never learn which path ran.

---

## How composition works

Rhei has no template-calls-template primitive, and artifact contracts may not
reference paths outside a workspace. So composition happens through **inputs and
outputs**: each template writes JSON artifacts, and the next takes their paths as
inputs and copies them in.

```
paper-ingest ──► paper.json ──┬──► reviewer-match ──► reviewer-matches.json ──► pc-citation-scan
                              │                                                        │
venue-intake ──► venue.json ──┼──► overall-review ──► overall-reviews.json ──┐         │
             └─► program-committee.json                                      │         │
                              ├──► section-review ──► section-reviews.json ──┤         │
                              │                                              │         │
                              └──► related-work  ──► related-work.json ──────┤         │
                                                                             ▼         ▼
                                                                     pc-member-review
                                                                             │
                                                              submission-<id>.txt
```

Every incoming artifact is checked at the boundary by
[`import_artifact.py`](scripts/import_artifact.py), which refuses to import a file
that is missing, is the wrong artifact, or violates its schema.

That check is the point. A stale or truncated `paper.json` caught at the boundary
costs one program invocation. The same file discovered after the fan-out costs a
full multi-model review — and may not be discovered at all, because a reviewer
handed half a paper produces confident, plausible, wrong output.

Every artifact declares its own `artifact` field, and every consumer states which
one it expects, so wiring the wrong upstream workspace into an input fails
immediately with a clear message rather than producing nonsense:

```
error: artifact mismatch importing `../venue/venue/venue.json`:
       expected 'paper', file declares 'venue'.
       A wrong upstream workspace is wired into this input.
```

---

## Validation

Nine schemas in [`schemas/`](schemas/), one per artifact. They are **closed**
(`additionalProperties: false`) and constrain ids, enums, and ranges — a
`likelihood` of 1.4, a `band` of `certain`, or a point id of `P-1` are all
rejected.

Validation runs in **program states**, not agent states. Whether a file conforms
to a schema is a decided question; letting a model answer it would defeat the
purpose of having a contract. Each producing template ends with:

```
write artifact ──► validate [program] ──exit 0──► completed
                       │
                       └──nonzero──► repair (bounded) ──► validate
                                          │
                                   attempts exhausted
                                          ▼
                                   <artifact>-failed [human gate]
```

The repair agent receives the validator's exact JSON-path errors. If it cannot fix
them within `repair_attempts`, the task parks on a human gate rather than passing
a malformed artifact downstream.

[`examples/`](examples/) holds one well-formed instance of every artifact. They
are checked in as both documentation — the agents writing these artifacts are
pointed at them — and as test fixtures.

---

## Configuring agents

Every template takes an `agents_json` input, written verbatim into the workspace's
`.agents/rhei/settings.json`. Any agent named in a selector must be declared there
or in your global rhei settings, **including the bracketed modes** — an undeclared
agent or mode fails instantiation.

The default declares `codex`; `claude-code` needs no declaration. To use something
else entirely:

```bash
cat > my-agents.json <<'JSON'
{ "gemini": { "command": ["gemini"], "model_flag": "--model", "stdin_prompt": true,
              "modes": { "yolo": ["--yolo"], "deep": ["--yolo", "--thinking", "high"] } } }
JSON

rhei instantiate overall-review --set-file agents_json=my-agents.json \
  --values my-personalities.yaml --output overall/
```

---

## Reviewer personalities

`overall-review` and `section-review` take a `personalities` array. A personality
is a **stance**, not just a model: each gets its own prompt *and* its own target,
and one state is generated per personality.

```yaml
# personalities.yaml
personalities:
  - id: academic
    label: Academic reviewer
    selector: claude-code[yolo]:anthropic:claude-opus-5
    stance: >-
      You are a professor reviewing for a top-tier venue. Prioritize novelty,
      technical soundness, and empirical rigor. Distinguish major from minor
      concerns, and never dismiss work you simply find unfashionable.
  - id: industry-skeptical
    label: Industry-skeptical reviewer
    selector: codex[high]:openai:gpt-5.6-sol
    stance: >-
      You are a performance architect who has been burned by overstated results.
      Default toward rejection unless the evidence is strong. Attack
      claim-to-evidence alignment sentence by sentence.
```

Two reviewers who would accept and reject the same paper for defensible reasons
tell you far more than two runs of the same prompt. The merge steps preserve that
disagreement instead of averaging it away; `pc-member-review` needs the unmerged
originals to see how many independent reviewers raised the same point.

---

## Running the whole pipeline

Each template becomes its own workspace, and later ones point at earlier ones:

```bash
mkdir review-42 && cd review-42

rhei instantiate paper-ingest ../submission-42.pdf --set paper_id=submission-42 --output ingest/
rhei run ingest/

rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA --output venue/
rhei run venue/

rhei instantiate related-work --set paper=../ingest/paper/paper.json --output related/
rhei instantiate overall-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json \
  --set related_work=../related/related/related-work.json \
  --values ../personalities.yaml --output overall/
rhei instantiate section-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json --output sections/

rhei run related/ && rhei run overall/ --parallel 4 && rhei run sections/ --parallel 4

rhei instantiate pc-member-review --set paper=../ingest/paper/paper.json \
  --set venue=../venue/venue/venue.json \
  --set overall_reviews=../overall/reviews/overall-reviews.json \
  --set section_reviews=../sections/reviews/section-reviews.json \
  --set related_work=../related/related/related-work.json --output review/
rhei run review/
```

Two human gates in `pc-member-review` stop the run: point curation, then final
sign-off.

**Author-side subset** — you are writing the paper, not reviewing it:

```bash
rhei run ingest/ && rhei run venue/
rhei instantiate reviewer-match   --set paper=../ingest/paper/paper.json \
  --set program_committee=../venue/venue/program-committee.json --output matches/
rhei instantiate pc-citation-scan --set paper=../ingest/paper/paper.json \
  --set reviewer_matches=../matches/matches/reviewer-matches.json \
  --set bibliography=../../paper/references.bib --output citations/
rhei run matches/ && rhei run citations/
```

That tells you who will likely read the paper and whose work you have not cited —
without running a single review.

---

## Layout

```
shared/
├── README.md                     This file
├── schemas/*.schema.json         The nine artifact contracts
├── examples/*.json               One valid instance per artifact
├── partials/                     Shared manifest and settings fragments
└── scripts/
    ├── validate_artifact.py      Dependency-free JSON Schema subset validator
    ├── import_artifact.py        Boundary check + copy between workspaces
    ├── gen_validation_states.py  Emits the validate/repair/gate block
    ├── gen_inputs_table.py       Emits a README inputs table from a manifest
    ├── test_contracts.sh         Schema + validator test suite
    └── test_templates.sh         Instantiate + validate + dry-run every template
```

Each template bundles copies of the scripts and the schemas it needs, because
`rhei instantiate` copies only that template's own directory.

## Tests

```bash
.agents/rhei/shared/scripts/test_contracts.sh   # 41 checks: schemas, validator, corruption, cross-wiring
.agents/rhei/shared/scripts/test_templates.sh   # 13 checks: every template + input branches + fan-out
```
