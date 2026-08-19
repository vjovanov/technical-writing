# The paper pipeline

**Eight composable rhei templates that hand each other schema-validated
artifacts.** Run one, run a few, or run all of them.

They live in `.agents/rhei/templates/`, so `rhei templates` and
`rhei instantiate <name>` find them by bare name from anywhere **inside this
repository**.

## Running them on a paper somewhere else

Templates here are *project-scoped*. Papers usually are not in this repository, so
pick one of these:

**Install once, use everywhere** (recommended) — symlink them into your user
template directory, where rhei looks second:

```bash
# from a checkout of this repository
mkdir -p ~/.agents/rhei/templates
for t in "$PWD"/.agents/rhei/templates/*/; do
  ln -sfn "$t" ~/.agents/rhei/templates/
done
rhei templates          # all eight now listed as `user` scope
```

Symlinks rather than copies, so a `git pull` here updates them. After this, every
command below works from any directory.

**Or name the template by path**, with no install:

```bash
rhei instantiate /path/to/technical-writing/.agents/rhei/templates/paper-ingest \
  ../submission-42.pdf --output paper-ingest/
```

The flows below use bare names and assume you installed.

---

## Which flow do I run?

Five flows cover almost everything. Each is copy-pasteable; pick by what you are
trying to find out.

| I want to… | Flow | Templates | Human gates |
|---|---|---|---|
| Write a review of someone's paper | [Reviewer](#1-reviewer) | 6 | 2 |
| Know who'll review mine, and what to cite | [Pre-submission recon](#2-pre-submission-recon) | 4 | 0 |
| Find my paper's weaknesses before reviewers do | [Mock review](#3-mock-review) | 5 | 0–2 |
| Check my related work is complete | [Related-work check](#4-related-work-check) | 2 | 0 |
| Dig into one weak section | [Section deep dive](#5-section-deep-dive) | 3 | 0 |

### Run it as one Panta project (recommended)

A rhei **project** has one Panta root, and any workspace directory dropped into it
becomes a rhei under that root. Do that with the pipeline and you get one graph
instead of eight loose workspaces: `rhei list` shows every ticket under its
project-qualified id, `rhei validate` checks the whole thing, and **a single
`rhei run` drives the pipeline in dependency order** — because `**Prior:**`
resolves across rheis.

Each template takes a `prior` input for exactly this. Leave it empty for a
standalone workspace; set it to the upstream tickets when the workspaces are
members of a project.

```bash
mkdir review-42 && cd review-42
rhei init --here --title "Review 42"

# Settings live at the project root. A member rhei's own settings.json is
# ignored — rhei warns about this, and it is the one thing to get right.
mkdir -p .agents/rhei
rhei instantiate paper-ingest ../submission-42.pdf --set paper_id=42 \
  --output paper-ingest/
cp paper-ingest/.agents/rhei/settings.json .agents/rhei/settings.json

rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA --output venue-intake/

rhei instantiate related-work   --set paper_id=42 --keep-on-error \
  --set prior='Task paper-ingest.ingest' --output related-work/
rhei instantiate overall-review --set paper_id=42 --keep-on-error \
  --set prior='Task paper-ingest.ingest, Task venue-intake.venue' --output overall-review/
rhei instantiate section-review --set paper_id=42 --keep-on-error \
  --set prior='Task paper-ingest.ingest, Task venue-intake.venue' --output section-review/

rhei validate                      # the whole project, all five rheis
rhei run --parallel 6              # one command drives all of them
```

#### Where the project lives

Two layouts. Both work; they trade zero configuration against having everything
in one place.

**Per paper (used above).** A project per paper, `rhei init --here` inside it. Rhei
names match template names, so every default path resolves and you pass none:

```
review-42/            <- rhei init --here
├── paper-ingest/
├── venue-intake/
├── overall-review/
└── ...
```

**One shared `~/panta` for every review.** `panta/` is the conventional name for a
user-level project, so `~/panta` is a natural home for all your reviews:
`rhei list` then shows every review you have ever run, and one `rhei run` advances
all of them.

Create it *in place*, not with `rhei init ~`:

```bash
mkdir -p ~/panta && cd ~/panta && rhei init --here --title "Reviews"
```

`rhei init ~` would put the project at `~/panta/` but also write `AGENTS.md` and
`.gitignore` into `$HOME` itself. The form above keeps all three files inside
`~/panta/` and leaves your home directory alone.

The catch: **rhei discovery does not descend into subdirectories** — rheis live
directly in the project root, so you cannot group a paper's workspaces in a
`review-42/` folder inside `~/panta`. Every rhei is a direct child, and rhei ids
must be unique across the whole project. So suffix them per paper, and pass the
upstream paths explicitly, since the defaults assume the unsuffixed names:

```bash
cd ~/panta
mkdir -p .agents/rhei             # settings go here, once, for every review

P=42
rhei instantiate paper-ingest ~/papers/submission-$P.pdf \
  --set paper_id=$P --output paper-ingest-$P/
cp paper-ingest-$P/.agents/rhei/settings.json .agents/rhei/settings.json

rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA \
  --output venue-intake-$P/

rhei instantiate overall-review --set paper_id=$P --keep-on-error \
  --set paper=../paper-ingest-$P/paper/paper.json \
  --set venue=../venue-intake-$P/venue/venue.json \
  --set prior="Task paper-ingest-$P.ingest, Task venue-intake-$P.venue" \
  --output overall-review-$P/

rhei validate && rhei run --parallel 6
```

Reviews for different papers are independent, so a project-wide `rhei run`
advances all of them concurrently.

**Which to use.** Per paper if you review a few papers a year and want the short
commands — the workspace is self-contained and you can archive or delete it whole.
Shared `~/panta` if you want one dashboard over everything, and do not mind the
suffixes and the explicit paths.

**Why `--keep-on-error`.** `rhei instantiate` validates its output *in isolation*,
before it is part of the project, so a cross-rhei `prior` fails that check with
"no rhei named 'paper-ingest' in this project". The workspace is still written
correctly. The project-level `rhei validate` on the next line is the check that
counts — if it passes, the wiring is right.

`rhei instantiate` still **exits non-zero** in this case, so a script running under
`set -e` will stop on it. Either drop `set -e` around these calls or append
`|| true`, and rely on the project-level validate to catch a genuine mistake.

**`pc-member-review` comes second.** `section-review`'s merge task is spawned at
run time by its coordinator, so it does not exist yet when the project is first
built, and a `prior` naming it cannot resolve. Add it once the reviews are done:

```bash
rhei instantiate pc-member-review --set paper_id=42 --keep-on-error \
  --set prior='Task overall-review.merge, Task section-review.merge' \
  --output pc-member-review/
rhei validate && rhei run
```

`rhei list` at any point shows the whole review as one tree:

```
Task paper-ingest.ingest: Ingest submission-42 [ingest]
Task venue-intake.venue: Resolve OOPSLA 2026 [resolve-venue]
Task venue-intake.committee: Harvest the program committee [harvest-pc] (prior: venue-intake.venue)
Task overall-review.import: Import and check the inputs [import-inputs] (prior: paper-ingest.ingest, venue-intake.venue)
Task overall-review.review-academic: Overall review — Academic reviewer [review-overall-academic] (prior: overall-review.import)
...
```

The flows below are written as standalone workspaces, which is simpler to read and
works without a project. To run any of them under Panta, add `rhei init --here`,
put the settings at the project root, add the `--set prior=...` shown above, and
replace the per-workspace `rhei run` calls with one project-wide `rhei run`.

---

### The one convention that matters

**Name each workspace after the template that made it.** Every template's
upstream inputs default to `../<template-name>/<its output path>`, so a pipeline
laid out that way wires itself and you never pass a path:

```
review-42/
├── paper-ingest/      → paper/paper.json
├── venue-intake/      → venue/venue.json, venue/program-committee.json
├── related-work/      → related/related-work.json
├── overall-review/    → reviews/overall-reviews.json
├── section-review/    → reviews/section-reviews.json
└── pc-member-review/  → review/submission-42.txt
```

Use different names if you like — then pass `--set paper=...` etc. explicitly.
The commands below use the convention.

---

### 1. Reviewer

**When:** you are on a PC, or reviewing for a journal, and have to submit a
review. This is what the old `paper-review` template did.

```bash
mkdir review-42 && cd review-42

# Read the paper once, and resolve the venue. Independent — run them together.
rhei instantiate paper-ingest ../submission-42.pdf --set paper_id=42 \
  --output paper-ingest/
rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA \
  --output venue-intake/
rhei run paper-ingest/ &
rhei run venue-intake/ &
wait

# What the paper must be judged against.
rhei instantiate related-work --set paper_id=42 --output related-work/
rhei run related-work/

# Two independent reads of the paper: whole-paper, and section by section.
rhei instantiate overall-review --set paper_id=42 --output overall-review/
rhei instantiate section-review --set paper_id=42 --output section-review/
rhei run overall-review/ --parallel 4
rhei run section-review/ --parallel 6

# Consolidate, verify, and render the venue's form. Stops at two human gates.
rhei instantiate pc-member-review --set paper_id=42 --output pc-member-review/
rhei run pc-member-review/
```

**You will be stopped twice.** At *point curation*, every consolidated point is in
front of you with an independent verifier's verdict; you set `human_action` and
that overrides the verifier in both directions. At *final sign-off*, you replace
every `[SUGGESTED]` score with your own and either approve or write
`review/human-feedback.md` and send it back.

Submit `pc-member-review/review/submission-42.txt`.

**Skip** `reviewer-match` and `pc-citation-scan` — they answer author-side
questions and tell a reviewer nothing.

---

### 2. Pre-submission recon

**When:** your paper is nearly done and you want to know who is likely to read it
and whose work you have not engaged with. No review runs, so this is the cheapest
and fastest flow.

```bash
mkdir recon && cd recon

rhei instantiate paper-ingest ../main.tex --set source_kind=latex \
  --set paper_id=submission --output paper-ingest/
rhei instantiate venue-intake https://2026.splashcon.org/track/OOPSLA \
  --output venue-intake/
rhei run paper-ingest/ && rhei run venue-intake/

rhei instantiate reviewer-match --set paper_id=submission \
  --values ../authors.yaml --output reviewer-match/
rhei run reviewer-match/

rhei instantiate pc-citation-scan --set paper_id=submission \
  --set bibliography=../references.bib --output pc-citation-scan/
rhei run pc-citation-scan/
```

`authors.yaml` supplies `author_names` so conflicts of interest are detected;
without it the template says so in `method` rather than silently reporting none.

**Read:** `reviewer-match/matches/reviewer-matches.json` for who is likely to
review, sorted by band, each with the evidence behind the estimate. Then
`pc-citation-scan/citations/pc-citations.json`, filtered to
`citation_priority: "must"` and `already_cited: false` — that short list is the
one that matters before a deadline.

---

### 3. Mock review

**When:** before you submit, to find what reviewers will say while you can still
do something about it.

Same as the [reviewer flow](#1-reviewer) but on your own paper, and worth
configuring adversarial personalities — a friendly mock review is a waste of
tokens:

```yaml
# harsh.yaml
personalities:
  - id: skeptic
    label: Skeptical architect
    selector: codex[xhigh]:openai:gpt-5.6-sol
    stance: >-
      Default to rejection. Attack claim-to-evidence alignment sentence by sentence:
      unfair baselines, missing ablations, absent variance, cherry-picked benchmarks.
      Do not fabricate flaws — every objection must cite concrete text.
  - id: outsider
    label: Adjacent-field reviewer
    selector: claude-code[yolo]:anthropic:claude-opus-5
    stance: >-
      You work in a neighbouring area and were assigned this paper. Flag every place
      the paper assumes context you do not have. If you cannot follow the argument,
      that is a finding, not your failing.
```

```bash
rhei instantiate overall-review --values harsh.yaml --set paper_id=submission --output overall-review/
rhei instantiate section-review --values harsh.yaml --set paper_id=submission --output section-review/
rhei run overall-review/ --parallel 4 && rhei run section-review/ --parallel 6
```

Stop there and read the two artifacts directly, or run `pc-member-review` as well
to get one deduplicated, independently verified list instead of several
overlapping ones. Verification matters most here: it kills the plausible-sounding
objections that would otherwise send you rewriting something that is already fine.

The "adjacent-field reviewer" is worth keeping. Real PCs assign papers to people
outside the sub-area, and that reviewer's confusion is the one that sinks papers.

---

### 4. Related-work check

**When:** you suspect the related-work section is thin, or a reviewer said so. Two
templates, no committee research, no reviews.

```bash
mkdir rw && cd rw
rhei instantiate paper-ingest ../main.tex --set source_kind=latex --output paper-ingest/
rhei run paper-ingest/
rhei instantiate related-work --set max_papers=30 --output related-work/
rhei run related-work/
```

**Read:** `related-work/related/related-work.json`, filtered to entries where
`relation` is `closest-prior` or `competing` **and** `cited_by_paper` is `false`.
That is the list that gets papers rejected for "insufficient comparison to prior
work". `queries[]` records what was searched, so you can widen the sweep and
re-run if it looks shallow.

---

### 5. Section deep dive

**When:** one section is the problem — usually the evaluation — and you want
several reviewers on it rather than on the whole paper.

Run `paper-ingest` and `venue-intake`, then **edit
`paper-ingest/paper/paper.json`** and mark every section except the ones you care
about as `boilerplate`:

```bash
rhei instantiate section-review --values harsh.yaml --output section-review/
rhei run section-review/ --parallel 4
```

`section-review` spawns one task per `core` section per personality, so those
marks are the cost control. Two sections × three personalities is six tasks;
leaving a twelve-section paper fully `core` is thirty-six.

Re-validate after editing by hand, since nothing downstream will accept a
malformed artifact:

```bash
cd paper-ingest && python3 scripts/validate_artifact.py \
  --schema-dir schemas --instance paper/paper.json --expect-artifact paper
```

---

## What runs in parallel, and what has to wait

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

- **`paper-ingest` and `venue-intake` are independent** — start them together.
- **`related-work`, `overall-review`, and `section-review` are independent of each
  other.** Reviews are better with the related-work index, so run it first if you
  want it used; if it is absent the reviews still run and say so.
- **Inside a workspace**, `--parallel N` fans out the personality tasks
  (`overall-review`) and the per-section tasks (`section-review`). Without it they
  serialize and you wait for no reason.
- **`pc-member-review` needs the overall and section reviews.** `related-work` and
  `pc-citations` are picked up automatically if those workspaces exist and skipped
  if they do not.

## Re-running one step

The point of splitting the old monolith. Each workspace is independent, so when
the venue's review form was harvested wrong, or a reviewer personality was too
soft, you redo that step alone:

```bash
rm -rf overall-review/
rhei instantiate overall-review --values better-personalities.yaml --output overall-review/
rhei run overall-review/ --parallel 4

rm -rf pc-member-review/          # re-consolidate against the new reviews
rhei instantiate pc-member-review --set paper_id=42 --output pc-member-review/
rhei run pc-member-review/
```

Nothing upstream re-runs. The paper is not re-read, the venue is not re-fetched,
and the literature is not re-swept.

`rhei reset <workspace>` puts a workspace back to its initial state without
deleting dynamically spawned task files — useful for a re-run with the same
configuration.

## What it costs, and the levers

Rough shape per template: `paper-ingest` and `venue-intake` are one agent pass
each; `related-work` is one pass plus searching; `overall-review` is one pass per
personality; `section-review` is (core sections × personalities); and
`pc-member-review` is three passes plus two human gates.

| Lever | Where | Effect |
|---|---|---|
| `core`/`boilerplate` marks | `paper.json` | Directly sets `section-review`'s task count |
| `personalities` | `overall-review`, `section-review` | Multiplies both review templates |
| `bands` | `pc-citation-scan` | `["high"]` scans far fewer people than `["high","medium"]` |
| `max_papers` | `related-work` | Caps the sweep |
| `max_papers_per_member` | `pc-citation-scan` | Caps per-person indexing |
| `repair_attempts` | all | Bounded retries on a schema failure |
| `render_passes` | `pc-member-review` | How many times you may send the review back |

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

`paper-ingest` is not one of the six review steps. It exists because "run the
review on a PDF or on LaTeX" is an *ingest* concern: it is settled once, there,
and the downstream templates read the same `paper.json` either way and never learn
which path ran.

---

## How composition works

Rhei has no template-calls-template primitive, and artifact contracts may not
reference paths outside a workspace. So composition happens through **inputs and
outputs**: each template writes JSON artifacts, and the next takes their paths as
inputs and copies them in.

Every incoming artifact is checked at the boundary by
[`import_artifact.py`](scripts/import_artifact.py), which refuses a file that is
missing, is the wrong artifact, or violates its schema.

That check is the point. A stale or truncated `paper.json` caught at the boundary
costs one program invocation. The same file discovered after the fan-out costs a
full multi-model review — and may not be discovered at all, because a reviewer
handed half a paper produces confident, plausible, wrong output.

Every artifact declares its own `artifact` field and every consumer states which
one it expects, so wiring the wrong workspace into an input fails immediately:

```
error: artifact mismatch importing `../venue-intake/venue/venue.json`:
       expected 'paper', file declares 'venue'.
       A wrong upstream workspace is wired into this input.
```

## Validation

Nine schemas in [`schemas/`](schemas/), one per artifact. They are **closed**
(`additionalProperties: false`) and constrain ids, enums, and ranges — a
`likelihood` of 1.4, a `band` of `certain`, or a point id of `P-1` are all
rejected.

Validation runs in **program states**, not agent states. Whether a file conforms
to a schema is a decided question; letting a model answer it would defeat the
purpose of the contract. Each producing template ends with:

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

[`examples/`](examples/) holds one well-formed instance of every artifact —
checked in as documentation the writing agents are pointed at, and as test
fixtures.

## Configuring agents

Every template takes an `agents_json` input, written verbatim into the workspace's
`.agents/rhei/settings.json`. Any agent named in a selector must be declared there
or in your global rhei settings, **including the bracketed modes** — an undeclared
agent or mode fails instantiation.

The default declares `codex`; `claude-code` needs no declaration. For anything
else:

```bash
cat > my-agents.json <<'JSON'
{ "gemini": { "command": ["gemini"], "model_flag": "--model", "stdin_prompt": true,
              "modes": { "yolo": ["--yolo"], "deep": ["--yolo", "--thinking", "high"] } } }
JSON

rhei instantiate overall-review --set-file agents_json=my-agents.json \
  --values my-personalities.yaml --output overall-review/
```

## Reviewer personalities

`overall-review` and `section-review` take a `personalities` array. A personality
is a **stance**, not just a model: each gets its own prompt *and* its own target,
and one state is generated per personality.

Two reviewers who would accept and reject the same paper for defensible reasons
tell you far more than two runs of the same prompt. The merge steps preserve that
disagreement instead of averaging it away; `pc-member-review` needs the unmerged
originals to see how many independent reviewers raised the same point.

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

Each template bundles copies of the scripts and schemas it needs, because
`rhei instantiate` copies only that template's own directory.

## Tests

```bash
.agents/rhei/shared/scripts/test_contracts.sh   # 41 checks: schemas, validator, corruption, cross-wiring
.agents/rhei/shared/scripts/test_templates.sh   # 13 checks: every template + input branches + fan-out
```
