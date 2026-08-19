# technical-writing

Tooling and templates for technical writing and peer review.

## Contents

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
