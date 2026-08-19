# Technical Writing

A small library for **AI–human collaboration on LaTeX papers**.

It gives you a way to mark, inside the `.tex` source, which text an AI agent may
rewrite and which it must leave alone — and a verification step that fails the
build when protected text is touched.

## Why

Ask an agent to "tighten the prose" and it will cheerfully rewrite the one
definition that took three reviewer cycles to settle. Instructions in a prompt
are advisory; these annotations are checkable.

| Annotation | Meaning |
|------------|---------|
| `\aikeep{text}` | Frozen. The agent must never modify it. |
| `\aianchor{text}` | Must stay the opening sentence of its paragraph, in its original order relative to other anchors. Surrounding prose is editable. |
| `\airule{text}` | A hard rule the agent must follow for the rest of the section. Invisible in the PDF. |
| `\aiguideline{text}` | A softer guideline, same section scope. Also written to `\jobname.aiguidelines` for tooling. |
| `\ainote{text}` | A to-do for the agent. Invisible in the PDF. |
| `\aireview[1-10]{text}{comment}` | Agent's review comment, cyan→blue by importance. |
| `\review[1-10]{text}{comment}` | Human's review comment, yellow→red by importance. |

`\aikeep` and `\aianchor` are enforced by `scripts/verify_aikeep.py`, which hashes
every protected block into `.aikeep-manifest.json`. `make verify` fails with a
non-zero exit code if any hash changed, if a block disappeared, or if two anchors
swapped order.

Hashes are computed over *whitespace-normalized* content, so re-wrapping a
paragraph does not fail the build — TeX collapses runs of whitespace anyway, and
a check that cries wolf on every reflow is a check people learn to ignore. Moving
a block to a different line is likewise fine; only its text is compared.

`\airule` and `\aiguideline` are **section-scoped**: they apply from where they
appear until the next `\section` of equal or higher level. That scoping is a
convention the agent honors, not something LaTeX checks.

## Layout

```
AGENTS.md              Instructions an AI agent reads before editing a paper
latex/aiwriting.sty    The LaTeX package defining every annotation
scripts/verify_aikeep.py   Manifest generation and verification
make/aiwriting.mk      Drop-in verify / verify-update / verify-list / verify-diff targets
agents/                Reviewer personas for adversarial self-review
templates/AGENTS.md    Skeleton AGENTS.md for a paper repository
example/               Minimal compilable paper exercising every annotation
```

## Using it in a paper

**1. Make the package findable.** Either copy `latex/aiwriting.sty` next to your
`main.tex`, or point `TEXINPUTS` at it from your Makefile:

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

Only the bracketed *comment* is toggled; the annotated text is always typeset, so
switching to a print-ready build never changes the paper's length.

**3. Add the verification targets** to your Makefile:

```make
include $(AIWRITING)/make/aiwriting.mk
```

**4. Create the manifest** once, then commit it:

```bash
make verify-update
git add .aikeep-manifest.json
```

**5. Point your agent at the rules.** In your paper's `AGENTS.md`, link to
[`AGENTS.md`](AGENTS.md) in this directory for the annotation semantics and keep only
paper-specific content (thesis, structure, results to preserve) locally.
[`templates/AGENTS.md`](templates/AGENTS.md) is a skeleton for exactly that.

## Commands

Run from the paper directory:

| Command | Purpose |
|---------|---------|
| `make verify` | Check protected content is unchanged. **Run after every `.tex` edit.** Exits non-zero on failure. |
| `make verify-update` | Regenerate the manifest. **Human approval only** — it makes any prior tampering pass forever. |
| `make verify-list` | List every protected block with its hash |
| `make verify-diff` | Show what changed since the manifest was written |

`verify` reports each change as `MODIFIED` (text edited), `REMOVED` (block or its
wrapper deleted), `NEW` (block added — a warning, not a failure) or
`ORDER VIOLATION` (anchors reordered). `MODIFIED` and `REMOVED` fail the build.

The script also runs standalone:

```bash
python3 scripts/verify_aikeep.py verify --root path/to/paper
```

## Example

`example/` is a self-contained paper using `article` (not `acmart`), so it builds
anywhere:

```bash
cd example
make          # print-ready build      -> main.pdf
make draft    # review comments shown  -> main-draft.pdf
make verify   # 6 protected blocks, passes
```

The draft build writes a **separate** `main-draft.pdf` on purpose. If both builds
shared one filename, latexmk — which decides what to rebuild from source
timestamps, and cannot see that a command-line option changed — would report
"nothing to do" and leave a PDF full of review comments sitting where you expect
the submission version.

## Package options

| Option | Effect |
|--------|--------|
| `showreviews` | Render `\review` and `\aireview` comments inline |
| `hidereviews` | Suppress them (default) |
| `noguidelinefile` | Do not write `\jobname.aiguidelines` |

## Requirements

- LaTeX with `xparse` and `xcolor` (both in TeX Live / MiKTeX base)
- `latexmk` for the Makefile targets. It needs the Perl modules `Time::HiRes`,
  `Unicode::Normalize` and `sigtrap`, which some minimal distro Perl builds omit
  (`dnf install perl-Time-HiRes perl-Unicode-Normalize perl-sigtrap`).
- Python 3.9+ for the verification script (no third-party packages)
- `pdftoppm` from `poppler-utils`, only for `make images`

Verified against TeX Live 2026 with `pdflatex`; the `example/` paper uses
`article` so it needs nothing beyond the above. Papers using `acmart` will
additionally need that class and the Libertinus fonts.
