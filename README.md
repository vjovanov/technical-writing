# technical-writing

Tooling and templates for technical writing and peer review.

## Contents

### [`ai-writing/`](ai-writing/) — LaTeX annotations for AI--human collaboration

Mark, in the `.tex` source, which sentences an AI agent may rewrite and which it
must leave alone — then make the build fail if it rewrites one it shouldn't.
A LaTeX package plus a verification script:

- **Protected text** — `\aikeep{}` freezes a span outright; `\aianchor{}` pins a
  topic sentence to its wording and to its order relative to other anchors. Both
  are hashed into a committed manifest.
- **`make verify`** — non-zero exit on modified, removed, or reordered protected
  content. Re-wrapping a line or moving a block is deliberately allowed, so the
  check does not cry wolf on ordinary editing.
- **Directives** — `\airule{}` and `\aiguideline{}` carry section-scoped
  instructions to the agent, invisible in the PDF; guidelines are also written to
  a sidecar file for tooling. `\ainote{}` leaves a to-do.
- **Reviews** — `\review{}` and `\aireview{}` attach a 1--10 importance rating and
  a comment, typeset inline only in a draft build, which is written to a separate
  file so review notes can never leak into the submission PDF.
- **Reviewer personas** — three stances (academic, industry-friendly,
  industry-skeptical) for adversarial self-review before submission.

```bash
cd ai-writing/example
make verify    # ✓ 6 protected block(s) unchanged
make           # print-ready PDF  -> main.pdf
make draft     # review comments  -> main-draft.pdf
```

See [`ai-writing/README.md`](ai-writing/README.md) for setup and exactly what is
and is not enforced, and [`ai-writing/AGENTS.md`](ai-writing/AGENTS.md) for the
rules agents are expected to follow.

### [`.agents/rhei/`](.agents/rhei/) — the paper pipeline

Eight composable [rhei](https://github.com/vjovanov/rhei) templates for reviewing
a conference paper, handing each other **schema-validated JSON artifacts**. They
live in `.agents/rhei/templates/`, so `rhei templates` and
`rhei instantiate <name>` find them automatically from anywhere in this
repository — no copying.

| Template | Answers |
|---|---|
| `paper-ingest` | What does this paper actually say? *(PDF or LaTeX — settled once, here)* |
| `venue-intake` | What does this venue select for, and who is on the committee? |
| `reviewer-match` | Which PC members are likely to review it, and on what evidence? |
| `pc-citation-scan` | Whose work should this paper be engaging with, and is it cited? |
| `related-work` | What does it have to beat? *(independent of the committee)* |
| `overall-review` | What do reviewers of different configurable stances make of it? |
| `section-review` | What is wrong section by section? *(tasks spawned from the paper's own section map)* |
| `pc-member-review` | What review do I submit? *(composes the rest, two human gates)* |

Composition runs through inputs and outputs: every handoff is a JSON artifact with
a schema, checked at the boundary before the consumer spends a token on it. A
wrong or stale file fails immediately with a clear message instead of producing
confident nonsense three steps later. Validation runs in **program states**, not
agent states — whether a file conforms to a schema is a decided question.

Run one template, a subset, or all eight. The author-side subset
(`reviewer-match` + `pc-citation-scan`) tells you who will likely read your paper
and whose work you have not cited, without running any review at all.

```bash
.agents/rhei/shared/scripts/test_contracts.sh   # schemas, validator, corruption, cross-wiring
.agents/rhei/shared/scripts/test_templates.sh   # every template + input branches + fan-out
```

See [`.agents/rhei/shared/README.md`](.agents/rhei/shared/README.md) for the
artifact graph, the schema contract, agent configuration, and a full end-to-end
invocation.

