# AI Agent Instructions

<!--
  Skeleton AGENTS.md for a paper repository using the `technical-writing` library.
  Replace every <PLACEHOLDER> and delete the guidance comments.
-->

This document provides instructions for AI agents working on this academic paper
submission.

**The annotation system, verification workflow, and general writing rules live in
the shared library:** [`<PATH_TO>/technical-writing/AGENTS.md`](../technical-writing/AGENTS.md).
Read that file first — it is authoritative for `\aikeep`, `\aianchor`, `\airule`,
`\aiguideline`, `\review`, `\aireview`, and the mandatory `make verify` step.
This file covers only what is specific to *this* paper.

## Paper Overview

**Title:** <TITLE>

**Target Venue:** <VENUE> (see [TARGET_CONFERENCE.md](TARGET_CONFERENCE.md))

**Main Thesis:** <ONE SENTENCE — the claim the whole paper defends>

## Paper Structure

```
main.tex                        # Main document, includes all sections
├── sections/abstract.tex       # Abstract and keywords
├── sections/introduction.tex   # Problem statement and contributions
├── ...                         # <LIST EACH SECTION AND ITS SUBSECTIONS>
└── references.bib              # Bibliography
```

## Key Technical Terms

<!-- Terms the AI must use consistently. One row per concept, never a synonym. -->

| Term | Definition |
|------|------------|
| <TERM> | <DEFINITION> |

## Key Results to Preserve

<!--
  Numbers from actual experiments. The AI must never change, round, or
  extrapolate these. Consider wrapping them in \aikeep{} in the .tex source
  so that `make verify` enforces this mechanically.
-->

### <SYSTEM / EXPERIMENT>
- <METRIC>: <VALUE>

## Paper-Specific Writing Guidelines

<!-- Only rules that do NOT already appear in the shared AGENTS.md. -->

1. <RULE>

## Custom LaTeX Commands

```latex
% Defined in main.tex preamble
\<macro>    % Renders "<OUTPUT>"
```

## Build Commands

| Command | Description |
|---------|-------------|
| `make` or `make pdf` | Build the PDF |
| `make watch` | Continuous compilation |
| `make images` | Convert PDF pages to PNG in `build/images/` |
| `make verify` | **REQUIRED after editing .tex files** |
| `make verify-update` | Update the manifest (human approval required) |
| `make clean` | Remove auxiliary files |
| `make distclean` | Remove all generated files |

## Files Reference

| File | Purpose |
|------|---------|
| `main.tex` | Document root with preamble and includes |
| `references.bib` | BibTeX bibliography |
| `comments.md` | Review comments and discussion |
| `TARGET_CONFERENCE.md` | Venue-specific guidelines |
| `images/` | All figures |
| `.aikeep-manifest.json` | Manifest of protected content hashes |
