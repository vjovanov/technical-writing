# AI Agent Instructions for Technical Writing

This document defines the annotation system, verification workflow, and writing
rules that AI agents must follow when editing LaTeX papers that use this library.

It is **paper-agnostic**. A paper repository adopting this library keeps its own
`AGENTS.md` describing that paper (thesis, structure, results to preserve) and
delegates the mechanics to this document — see
[`templates/AGENTS.md`](templates/AGENTS.md) for a ready-made skeleton.

## Annotation System

Use these LaTeX-style annotations to communicate between humans and AI.
They are provided by [`latex/aiwriting.sty`](latex/aiwriting.sty).

### AI Annotations

| Annotation | Purpose | Example |
|------------|---------|---------|
| `\aikeep{text}` | Protect text from AI modifications. The AI must NEVER modify this content. | `\aikeep{This definition is final.}` |
| `\aianchor{text}` | Anchor for the first sentence of a paragraph. The AI must preserve this as the paragraph's opening sentence and should not relocate or remove it. Used to mark key topic sentences that establish paragraph structure. | `\aianchor{Static profiling presents unique challenges.}` |
| `\aireview[<1-10>]{text}{comment}` | AI review of text with importance rating (1=low/cyan, 10=critical/blue) | `\aireview[7]{unclear phrase}{Consider rephrasing for clarity}` |
| `\ainote{text}` | Note for the AI to address in a future edit. Invisible in PDF. | `\ainote{Add a citation once the artifact DOI is assigned}` |
| `\airule{text}` | Rule that AI must follow. **Section-scoped** (see below). Invisible in PDF. | `\airule{All performance numbers must match evaluation section}` |
| `\aiguideline{text}` | AI guideline for agents. **Section-scoped** (see below). Invisible in PDF. | `\aiguideline{Use only values that appear in cited tables/figures}` |

#### Section Scoping for `\airule` and `\aiguideline`

Both `\airule` and `\aiguideline` are **section-scoped**: they apply from where they are placed until the end of the current section (including all nested subsections).

| Aspect | Behavior |
|--------|----------|
| **Start** | Rule/guideline activates at the line where it appears |
| **End** | Rule/guideline expires at the next `\section{}` of equal or higher level |
| **Inheritance** | Subsections inherit all active rules from parent sections |
| **Nesting** | Rules placed in a `\subsection{}` only apply to that subsection and its nested content |

**Example:**

```latex
\section{Evaluation}  % Section 5
\airule{Performance numbers must reference Table 2}
% ↳ applies to all of Section 5 (5.1, 5.2, 5.3, 5.4)

\subsection{Control Split Results}  % 5.1
\aiguideline{Use percentage format with 2 decimal places}
% ↳ both \airule AND \aiguideline apply here

\subsection{Method Hotness Results}  % 5.2
% ↳ only the \airule applies here (guideline was subsection-scoped to 5.1)

\section{Related Work}  % Section 6
% ↳ neither rule nor guideline applies - new section started
```

Scoping is a **convention the agent enforces**, not something LaTeX checks. Both
commands expand to nothing in the PDF; `\aiguideline` additionally writes its
text to `\jobname.aiguidelines` so external tooling can collect the guidelines
in document order.

### ⚠️ MANDATORY: Protected Content Verification

**After editing ANY `.tex` file, the AI MUST run:**

```bash
make verify
```

This verifies that `\aikeep{}` and `\aianchor{}` protected content has not been accidentally modified. If verification fails, the AI must immediately undo the offending changes.

**Verification commands:**

| Command | Purpose |
|---------|---------|
| `make verify` | Verify protected content is unchanged (MUST run after edits) |
| `make verify-update` | Update manifest after INTENTIONAL changes (requires human approval) |
| `make verify-list` | List all protected blocks (both `\aikeep` and `\aianchor`) |
| `make verify-diff` | Show changes since last manifest |

The underlying script is [`scripts/verify_aikeep.py`](scripts/verify_aikeep.py); the
`make` targets above come from [`make/aiwriting.mk`](make/aiwriting.mk).

The manifest file (`.aikeep-manifest.json`) tracks all protected content with SHA-256 hashes. It should be committed to version control.

**Difference between `\aikeep` and `\aianchor`:**

- `\aikeep{text}` — The text is completely frozen. AI cannot modify it under any circumstances.
- `\aianchor{text}` — The text must remain as the opening sentence of its paragraph. AI may edit surrounding content but must preserve the anchor's position and wording. **The relative order of anchors within a file is also verified** — if anchor A appeared before anchor B in the manifest, this order must be maintained.

Both annotations are verified by the same system and will cause verification failures if modified.

**Never run `make verify-update` on your own initiative.** Regenerating the
manifest makes any unauthorized change to protected content pass verification
forever after. Run it only when a human explicitly approves the change.

### Human Annotations

| Annotation | Purpose | Example |
|------------|---------|---------|
| `\review[<1-10>]{text}{comment}` | Human review of text with importance rating (1=low/yellow, 10=critical/red) | `\review[8]{this section}{Needs restructuring}` |

Human `\review` annotations take precedence over AI `\aireview` annotations.
Do not delete a `\review` until the issue it raises has been addressed.

### Review Visibility

`\review` and `\aireview` render their comment inline only when the package is
loaded with the `showreviews` option:

```latex
\usepackage[showreviews]{aiwriting}  % drafting: comments visible
\usepackage{aiwriting}               % print-ready: comments hidden (default)
```

The annotated text itself is always typeset; only the bracketed comment is
toggled. This means switching to a print-ready build never changes the paper's
content or length.

## Writing Guidelines

1. **Technical Precision**: Use exact terminology consistently. Pick one term per
   concept and never alternate synonyms (e.g. "control-split", not sometimes
   "branch split").
2. **Quantitative Claims**: All performance numbers must have citations or
   experimental backing. Never invent, round, or extrapolate a number that does
   not appear in a table, figure, or cited source.
3. **Contribution Clarity**: Preserve the structure of the contributions list in
   the introduction. Do not add, drop, or reorder contributions.
4. **Figure References**: Always reference figures and tables when discussing
   visual content.
5. **Citation Style**: Use `\cite{}` and never write a bibliography entry inline.
   Do not add a citation for a work you cannot name concretely.
6. **Paragraph Structure**: Preserve topic sentences. If a paragraph opens with an
   `\aianchor`, everything after it must support that sentence.
7. **Scope of Edits**: Make the edit that was asked for. Do not opportunistically
   rewrite adjacent prose, renumber sections, or reformat untouched files.

## Build Commands

A paper using this library is expected to expose these targets:

| Command | Description |
|---------|-------------|
| `make` or `make pdf` | Build the PDF |
| `make watch` | Continuous compilation (rebuilds on file changes) |
| `make images` | Convert PDF pages to PNG images in `build/images/` |
| `make verify` | **REQUIRED after editing .tex files** — verify protected content |
| `make verify-update` | Update the protected-content manifest (after human-approved changes) |
| `make clean` | Remove auxiliary files |
| `make distclean` | Remove all generated files including PDF and build directory |

### Reading the PDF

To inspect the rendered result, generate page images and read them:

```bash
make images
```

This creates PNG images at 300 DPI in `build/images/` with naming pattern
`page-1.png`, `page-2.png`, etc. Requires `pdftoppm` from the `poppler-utils`
package (`sudo apt install poppler-utils` on Debian/Ubuntu).

## Review Personas

[`agents/`](agents/) holds reviewer personas for adversarial self-review before
submission. Use them to pressure-test a draft, not to generate text for the paper:

| Persona | Stance |
|---------|--------|
| [`mit-professor-reviewer.md`](agents/mit-professor-reviewer.md) | Academic, methodical, balanced; novelty and rigor |
| [`industry-friendly-reviewer.md`](agents/industry-friendly-reviewer.md) | Constructive; looks for reasons to accept |
| [`industry-skeptical-reviewer.md`](agents/industry-skeptical-reviewer.md) | Adversarial; rejects unless evidence is strong |

[`agents/reviewer-personalities.md`](agents/reviewer-personalities.md) summarizes all three.

## Files Reference

| File | Purpose |
|------|---------|
| `latex/aiwriting.sty` | LaTeX package defining all annotation commands |
| `scripts/verify_aikeep.py` | Verification script for protected content |
| `make/aiwriting.mk` | Reusable `verify*` Make targets |
| `agents/` | Reviewer personas for adversarial self-review |
| `templates/AGENTS.md` | Skeleton `AGENTS.md` for a paper repository |
| `example/` | Minimal compilable paper exercising every annotation |
