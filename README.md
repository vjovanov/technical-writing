# technical-writing

Tooling and templates for technical writing and peer review.

## Contents

### [`ai-writing/`](ai-writing/) — LaTeX annotations for AI--human collaboration

A LaTeX package plus verification tooling for editing papers alongside AI agents.
It lets you mark, in the `.tex` source, which text an agent may rewrite and which
it must leave alone, and turns that intent into a check that fails the build:

- **Protected text** — `\aikeep{}` freezes a span outright; `\aianchor{}` pins a
  topic sentence to the start of its paragraph and to its position relative to
  other anchors. Both are hashed into a committed manifest.
- **Directives** — `\airule{}` and `\aiguideline{}` carry section-scoped
  instructions to the agent, invisible in the PDF; guidelines are also written to
  a sidecar file for tooling. `\ainote{}` leaves a to-do.
- **Reviews** — `\review{}` and `\aireview{}` attach a 1--10 importance rating
  and a comment, rendered inline only in a draft build.
- **`make verify`** — fails with a non-zero exit code on modified, removed, or
  reordered protected content, and is meant to run after every `.tex` edit.
- **Reviewer personas** — three stances (academic, industry-friendly,
  industry-skeptical) for adversarial self-review before submission.

See [`ai-writing/README.md`](ai-writing/README.md) for setup and
[`ai-writing/AGENTS.md`](ai-writing/AGENTS.md) for the rules agents are expected
to follow. [`ai-writing/example/`](ai-writing/example/) is a self-contained paper
exercising every annotation.

### [`paper-review/`](paper-review/) — rhei template

A multi-model conference paper review pipeline, packaged as a
[rhei](https://github.com/vjovanov/rhei) template. One instantiation reviews one paper:

- **Ingest** — resolves the venue (website, file, or name) into reviewer
  guidelines and the review form; renders the PDF page-by-page and produces a
  canonical full-text extraction plus a digest (section map, claimed
  contributions, key claims).
- **Related work** — searches the literature and downloads openly accessible
  PDFs into a ranked index.
- **Review fan-out** — two reviewer models independently summarize the paper
  and review every core section, plus dedicated evaluation and related-work
  passes. Review topics are derived from what the paper actually contains.
- **Aggregate and verify** — an aggregator merges all findings into
  addressable points `P-xxx`; a separate verifier classifies each point
  `confirmed` / `weakened` / `rejected` with evidence. Rejected points never
  reach the report.
- **Human gates** — three of them: intake approval, point curation, and final
  sign-off on scores. The human is the author of the outward-facing review.

Output is a submission-ready review plus a traceable long form that keeps
`[P-xxx]` markers back to the verified points.

Install by copying into `~/.agents/rhei/templates/`:

```bash
cp -r paper-review ~/.agents/rhei/templates/
```

See [`paper-review/README.md`](paper-review/README.md) for inputs, the state
machine, and instantiation examples.

#### Note on model targets

The bundled `settings.json` declares a `codex` agent resolved from `PATH`, and
the template defaults to Codex and Claude reviewer targets. Adjust the
selectors in `template.yaml` (or override with `--values`) for the models you
actually have.
