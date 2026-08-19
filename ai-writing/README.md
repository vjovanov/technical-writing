# ai-writing

**Tell an AI agent which sentences it may rewrite — and make the build fail if it
rewrites one it shouldn't.**

A LaTeX package (`aiwriting.sty`) plus a verification script. Together they turn
"please don't touch the definition in §2" from a hopeful instruction into a
check with an exit code.

---

## The problem

Ask an agent to *"tighten the prose"* and it will cheerfully improve the one
definition that took three reviewer cycles to settle. It is not being careless —
nothing in the file marks that sentence as different from any other.

Prompts are advisory. Annotations are checkable:

```latex
\aikeep{A \emph{protected block} is a span of text that an AI agent must never modify.}
Surrounding prose remains editable, so an agent can still improve this paragraph.
```

```console
$ make verify
✗ Verification failed
  MODIFIED [\aikeep]: sections/introduction.tex:12
    Original: A \emph{protected block} is a span of text that an AI agent ...
    Current:  A \emph{protected block} is a chunk of text that an AI agent...
```

Non-zero exit. Your CI, your pre-commit hook, and your agent's own workflow all
notice.

---

## Quickstart

```bash
cd example
make verify    # ✓ 6 protected block(s) unchanged
make           # print-ready PDF  -> main.pdf
make draft     # review comments  -> main-draft.pdf
```

`example/` is a complete two-page paper exercising every annotation. It uses
`article`, not `acmart`, so it builds with a stock TeX Live and nothing else.

Now break something on purpose:

```bash
sed -i 's/is a span of text/is a chunk of text/' sections/introduction.tex
make verify    # fails, and names the file, line, and both versions
```

---

## The annotations

| Annotation | Purpose | Visible in PDF? |
|------------|---------|-----------------|
| `\aikeep{text}` | Frozen. The agent must never modify it. | yes, as plain text |
| `\aianchor{text}` | A paragraph's topic sentence. Must keep its wording and its order relative to other anchors. Surrounding prose stays editable. | yes, as plain text |
| `\airule{text}` | A hard rule the agent must follow for the rest of the section. | no |
| `\aiguideline{text}` | A softer preference, same scope. Also written to `\jobname.aiguidelines` for tooling. | no |
| `\ainote{text}` | A to-do for the agent to pick up later. | no |
| `\aireview[1-10]{text}{comment}` | The agent's review comment. Cyan → blue by importance. | draft builds only |
| `\review[1-10]{text}{comment}` | A human's review comment. Yellow → red by importance. | draft builds only |

`\airule` and `\aiguideline` are **section-scoped**: they apply from where they
appear until the next `\section` of equal or higher level, and subsections
inherit from their parent.

---

## What is actually enforced

Worth being precise about, because the value of the check is knowing exactly what
it does and does not promise.

**Mechanically verified** by `make verify` — these fail the build:

- The text inside every `\aikeep{}` and `\aianchor{}` is byte-for-byte unchanged
  after whitespace normalization.
- No protected block was deleted, and neither was its wrapper. Stripping
  `\aikeep{...}` down to `...` is reported as a removal.
- `\aianchor` blocks appear in the same relative order within each file.

**Convention only** — the agent is told these in [`AGENTS.md`](AGENTS.md), but
nothing checks them:

- That an `\aianchor` is genuinely the *first* sentence of its paragraph.
- That `\airule` and `\aiguideline` were obeyed, or that their section scope was
  respected.
- Everything in the writing-guidelines section (terminology consistency,
  quantitative claims having backing, and so on).

**Deliberately allowed**, so the check does not cry wolf:

- **Re-wrapping lines.** Hashes cover whitespace-normalized content. TeX collapses
  runs of whitespace anyway, so a reflow changes the source bytes but not one
  glyph of output. A check that failed on every reflow is one people learn to
  ignore.
- **Moving a block.** Only text is compared, never line numbers. Inserting a
  paragraph above a protected block is not a change to it.
- **Adding new protected blocks.** Reported as `NEW`, a warning, not a failure.

---

## What failure looks like

```console
$ make verify
======================================================================
VERIFICATION FAILED: Protected content has been modified!
======================================================================
  MODIFIED [\aikeep]: sections/introduction.tex:12
    Original: A \emph{protected block} is a span of text that an AI agent ...
    Current:  A \emph{protected block} is a chunk of text that an AI agent...
  REMOVED [\aikeep]: sections/evaluation.tex:23
    Content: Protected blocks tracked

✗ Verification failed
make: *** [verify] Error 1
```

| Report | Meaning | Fails build |
|--------|---------|-------------|
| `MODIFIED` | The text inside a protected block was edited | yes |
| `REMOVED` | The block, or just its `\aikeep{}`/`\aianchor{}` wrapper, is gone | yes |
| `ORDER VIOLATION` | Two `\aianchor` blocks swapped places | yes |
| `NEW` | A protected block was added since the manifest | no — warning |

---

## Adding it to a paper

**1. Make the package findable.** Copy `latex/aiwriting.sty` next to your
`main.tex`, or point `TEXINPUTS` at it:

```make
AIWRITING = ../technical-writing/ai-writing
export TEXINPUTS := .:$(AIWRITING)/latex:$(TEXINPUTS)
```

The trailing colon matters — it tells TeX to also search its default paths.

**2. Load it in the preamble**, replacing any inlined annotation definitions:

```latex
\usepackage{aiwriting}               % print-ready: review comments hidden
\usepackage[showreviews]{aiwriting}  % drafting: review comments visible
```

**3. Add the verification targets** to your Makefile:

```make
include $(AIWRITING)/make/aiwriting.mk
```

**4. Create the manifest** once, then commit it — it is the record of what is
protected, and it belongs in version control next to the text it guards:

```bash
make verify-update
git add .aikeep-manifest.json
```

**5. Point your agent at the rules.** Have your paper's `AGENTS.md` link to
[`AGENTS.md`](AGENTS.md) here for the annotation semantics, and keep only
paper-specific content — thesis, structure, results to preserve — local.
[`templates/AGENTS.md`](templates/AGENTS.md) is a skeleton for exactly that.

---

## Commands

From the paper directory. The first four come from `make/aiwriting.mk`; the rest
are in the example's Makefile and are worth copying.

| Command | Purpose |
|---------|---------|
| `make verify` | Check protected content. **Run after every `.tex` edit.** Non-zero exit on failure. |
| `make verify-update` | Regenerate the manifest. **Human approval only** — see the warning below. |
| `make verify-list` | List every protected block with its hash |
| `make verify-diff` | Show what changed since the manifest was written |
| `make` / `make pdf` | Print-ready build → `main.pdf` |
| `make draft` | Review comments visible → `main-draft.pdf` |
| `make watch` | Rebuild continuously on file change |
| `make images` | Render `main.pdf` to PNGs in `build/images/` |
| `make draft-images` | Same for `main-draft.pdf` |
| `make clean` / `make distclean` | Remove aux files / everything generated |

> **Never let an agent run `make verify-update` on its own initiative.**
> Regenerating the manifest makes *any* unauthorized change to protected content
> pass verification from then on. It is the one command that can silently undo
> the entire guarantee.

The script runs standalone too:

```bash
python3 scripts/verify_aikeep.py verify --root path/to/paper
python3 scripts/verify_aikeep.py list --root path/to/paper
```

---

## Draft vs print-ready

The two builds write **different files** — `main.pdf` and `main-draft.pdf` — and
that separation is load-bearing. `latexmk` decides what to rebuild from source
timestamps and cannot see that a command-line option changed. If both wrote
`main.pdf`, then running `make` after `make draft` would report *"nothing to
do"* and leave a PDF full of internal review comments exactly where you expect
the submission version.

**Reviews are typeset material.** Hiding them never removes your own prose, but
showing them adds text and can repaginate the document — in a stress test, a
one-page document with twelve review comments became two pages. Check your page
count against `main.pdf`, never `main-draft.pdf`.

---

## Package options

| Option | Effect |
|--------|--------|
| `showreviews` | Render `\review` and `\aireview` comments inline |
| `hidereviews` | Suppress them (default) |
| `noguidelinefile` | Do not write `\jobname.aiguidelines` |

---

## Reviewer personas

[`agents/`](agents/) holds three reviewer stances for pressure-testing a draft
before submission. Use them to find problems, not to generate paper text.

| Persona | Stance |
|---------|--------|
| [MIT professor](agents/mit-professor-reviewer.md) | Academic and methodical; novelty, rigor, six scored categories |
| [Industry-friendly](agents/industry-friendly-reviewer.md) | Looks for reasons to accept; every criticism carries a fix |
| [Industry-skeptical](agents/industry-skeptical-reviewer.md) | Rejects unless evidence is strong; hunts unfair baselines and missing variance |

---

## Layout

```
AGENTS.md                  Rules an AI agent reads before editing a paper
README.md                  This file
latex/aiwriting.sty        The LaTeX package defining every annotation
scripts/verify_aikeep.py   Manifest generation and verification
make/aiwriting.mk          Includable verify / verify-update / verify-list / verify-diff
agents/                    Reviewer personas for adversarial self-review
templates/AGENTS.md        Skeleton AGENTS.md for a paper repository
example/                   Minimal compilable paper exercising every annotation
```

---

## Requirements

- **LaTeX** with `xparse` and `xcolor` — both present in a standard TeX Live or
  MiKTeX install. Verified on TeX Live 2026 with `pdflatex` and `xelatex`.
- **`latexmk`** for the Makefile targets. It needs the Perl modules
  `Time::HiRes`, `Unicode::Normalize` and `sigtrap`. Most distributions ship
  these with Perl itself, but Fedora/RHEL split them into separate packages that
  a minimal install omits:
  ```bash
  sudo dnf install perl-Time-HiRes perl-Unicode-Normalize perl-sigtrap
  ```
  Check with `perl -MTime::HiRes -MUnicode::Normalize -Msigtrap -e 'print "ok\n"'`.
- **Python 3.9+** for the verification script — standard library only, no
  third-party packages, no virtualenv.
- **`pdftoppm`** from `poppler-utils`, only for `make images` / `make draft-images`.

The `example/` paper needs nothing beyond the above. A paper using `acmart` will
additionally need that class and the Libertinus fonts.

## Troubleshooting

| Symptom | Cause |
|---------|-------|
| `File 'aiwriting.sty' not found` | `TEXINPUTS` is missing its trailing colon, or the path does not point at `ai-writing/latex` |
| `verify` fails right after cloning | The committed manifest is stale. Run `make verify-diff` to see what drifted before regenerating. |
| `MODIFIED` where `Original:` and `Current:` look identical | Truncated at 60 characters — the difference is further into the block. Use `make verify-diff` for full text. |
| `Can't locate Time/HiRes.pm` | `latexmk`'s Perl dependencies — see Requirements |
| Review comments in your submission PDF | You submitted `main-draft.pdf`. The print-ready file is `main.pdf`. |
