# Literature Wiki Project Plan and Status

## Purpose

This document records:

1. What was originally proposed for the bibliography-first literature wiki workflow.
2. What has actually been implemented in the repo so far.
3. What is still not aligned with the original intent or your expectations.
4. What remains to be done to get the project to a reliable, usable state.

The goal is to make the current state explicit so future work does not continue from incorrect assumptions.

---

## Original Intent and Proposed Direction

The project discussion evolved from a keyword-linking / bibliography-linking tool into a broader bibliography-first literature wiki pipeline for Obsidian.

The intended workflow we discussed was:

- `regex-tag.bib` is the canonical bibliography registry.
- Every ingested scholarly source must resolve to a valid bibliography entry before it becomes a managed wiki source note.
- The canonical bibliography identity remains the citekey.
- Existing bibliography notes in the vault such as `@citekey.md` remain separate from generated source notes.
- Generated source-note filenames use `<citekey>_wiki.md`.
- Generated source notes are bibliography-linked literature notes based on `specs/lit-note-template.md`.
- All authors and editors from BibTeX must be preserved in YAML as numbered fields.
- Raw source artifacts should be handled in an input queue and archived after processing.
- Generated source notes should be part of a managed wiki layer with index/log/overview pages.
- PDFs and EPUBs should be extracted into canonical text/markdown before summarization.
- Local-first LLM use via LM Studio is the default, with optional approval-gated cloud fallback later.
- Keyword CSV data should guide enrichment conservatively, not overwhelm notes with irrelevant metadata.
- `Related References` should contain only cited works in the source that deterministically match the bibliography.

The intended operating model was therefore:

- Raw inputs are immutable source artifacts.
- Extracted text is an intermediate processing artifact.
- Generated notes are the public wiki output.
- Bibliography links remain canonical and separate from `_wiki` note filenames.

---

## Major Plans That Were Proposed

### 1. Public-safe repo and config structure

Proposed:

- keep public config safe
- keep local secrets and live provider settings out of tracked files
- support local and optional cloud providers
- add watch-folder queueing

### 2. Bibliography registry and YAML fidelity

Proposed:

- parse `regex-tag.bib`
- preserve entry type, year, abstract, DOI, ISBN, authors, and editors
- emit:
  - `key: "[[@citekey]]"`
  - `type: "[[@entry_type]]"`
  - all `author - N`
  - all `editor - N`

### 3. Deterministic source matching

Proposed:

- markdown sources: use YAML `citation-key`
- EPUB packages: use `iTunesMetadata.plist`
- PDFs: use `[Title]_[Authors]_[year].pdf`
- uncertain matches go to review, not silent ingest

### 4. Extraction pipeline

Proposed:

- extract PDFs to canonical text/markdown
- ingest EPUBs through markdown or XHTML conversion
- clean extracted text before model use
- store extracted artifacts separately from raw inputs and final notes

### 5. Template-driven source notes

Proposed:

- generate `wiki/sources/<citekey>_wiki.md`
- preserve bibliography metadata in YAML
- populate note body from template sections
- re-ingest updates existing notes rather than duplicating them

### 6. Managed wiki layer

Proposed:

- maintain `wiki/index.md`, `wiki/log.md`, and `wiki/overview.md`
- add concept/entity pages
- support graph generation and linting

### 7. Watch folder and sequential queueing

Proposed:

- input queue folder
- one file at a time
- archive successful inputs to `processed/`
- archive failed or review-blocked inputs to `other/`
- show completion dialog

### 8. Approval-gated fallback models and keyword enrichment

Proposed:

- local model is primary
- fallback APIs require per-file approval
- budgets and daily caps are enforced
- keyword CSV supports guidance and conservative enrichment

---

## What Has Been Implemented So Far

This section describes the current repo state, not the intended end state.

### A. A `lit_wiki` package and CLI now exist

Implemented:

- new `src/lit_wiki/` package
- `main.py` delegates to a CLI with commands for:
  - `bib sync`
  - `source register`
  - `extract`
  - `ingest`
  - `watch run`
  - `graph build`
  - `lint`

Current status:

- this is real and wired up
- unit tests exist for core workflows

### B. Bibliography parsing and YAML generation have been implemented

Implemented:

- BibTeX parsing from `regex-tag.bib`
- ordered author/editor extraction
- numbered `author - N` and `editor - N` YAML emission
- `key: "[[@citekey]]"`
- `type: "[[@entry_type]]"`
- `_wiki` filenames for generated source notes

Current status:

- this part is largely aligned with the original plan
- tests cover author/editor YAML and `_wiki` naming

### C. Deterministic source matching has been implemented

Implemented:

- markdown matching via YAML `citation-key`
- EPUB matching via `iTunesMetadata.plist`
- PDF matching via `[Title]_[Authors]_[year]`

Current status:

- this exists and is test-covered
- uncertain matches still route to review states, but the review UX is still basic

### D. Watch-folder processing has been implemented

Implemented:

- `watch/` queue processing
- `watch/processed/`
- `watch/other/`
- sequential file processing
- summary dialogs

Current status:

- this works in the current code
- live smoke tests processed sample PDFs sequentially

### E. Local provider path and fallback scaffolding have been implemented

Implemented:

- provider abstraction
- LM Studio local model support
- fallback provider structure
- budget policy scaffolding
- approval callback flow

Current status:

- local LM Studio processing has been exercised live
- fallback logic is implemented and unit-tested
- live cloud fallback has not been fully validated in this repo because API keys were not configured

### F. PDF extraction was initially weak, then improved

Originally implemented:

- extraction relied on `mdls`, which failed on the sample PDFs

Then changed:

- `pypdf` added as the primary PDF extractor
- extraction cleanup added:
  - control character stripping
  - Unicode normalization
  - basic line-wrap cleanup
  - JSTOR/download boilerplate stripping

Current status:

- extraction is substantially better than the initial implementation
- sample PDF extraction now passes tests and no longer emits the earlier garbage text or NUL-byte contamination

### G. Related-reference handling was initially wrong, then partially repaired

Originally implemented:

- related references were inferred by scanning extracted text for bibliography title substrings
- this caused impossible matches such as 1998/2001 papers “citing” 2015/2022 works
- generic titles like `Introduction` and `Conclusion` caused false positives

Then changed:

- removed naive full-text title matching
- current resolver now prefers:
  - explicit citekeys
  - DOI hits
  - parsed references-section title matches
- generic-title filtering and future-year rejection were added
- rendered links now use `[[@citekey]]` instead of assumed `_wiki` pages

Current status:

- the most obviously wrong future-reference outputs have been fixed
- this is safer than before
- it is still a conservative resolver, not a full scholarly citation parser

### H. Keyword enrichment was initially far too noisy, then tightened

Originally implemented:

- keyword enrichment added many irrelevant tags and `see also` links
- cluster values and unrelated vocabulary polluted frontmatter
- examples included `UN`, `UCL`, `WWW`, `ITS`, `London`, `Psychology`

Then changed:

- enrichment split into:
  - guidance targets for prompts
  - conservative metadata links/tags for note output
- metadata caps were added
- broad stop rules were added
- general-only terms and single-word terms were restricted
- BibTeX keywords are deduped more carefully

Current status:

- frontmatter is much cleaner than the earlier state
- however, this still needs stronger semantic tuning to fully match your expectations

### I. Publish gating has been added

Implemented:

- ingest now validates notes before writing them
- issues that now block publish include:
  - broken bibliography links in `Related References`
  - future-dated related references
  - extraction contamination
  - metadata overrun beyond configured caps
  - malformed or duplicated section content

Current status:

- this is in place and helps prevent the worst garbage from being written
- it does not yet guarantee high-quality scholarship-aware synthesis

### J. Linting has been expanded

Implemented:

- lint now checks:
  - raw sources under `wiki/`
  - broken wiki links
  - broken bibliography links
  - future-dated references
  - extraction artifacts
  - suspiciously large metadata blocks

Current status:

- lint is more useful than before
- it is still mostly structural and does not judge summary quality deeply

### K. README/config/docs have been partially rewritten

Implemented:

- top-level README rewritten to reflect the literature-wiki workflow
- config example updated to document the watch-folder model and conservative keyword settings
- requirements expanded for extraction and matching support

Current status:

- docs are closer to the intended workflow than before
- but the repo still contains legacy config and older assumptions that can confuse the actual operating model

---

## What Has Been Verified

### Unit tests

Verified:

- current test suite passes
- test coverage now includes:
  - bibliography parsing
  - note rendering
  - deterministic matching
  - extraction cleanup
  - watch-folder archiving
  - conservative related-reference behavior
  - lint flagging raw sources under `wiki/`

### Live behavior

Verified live:

- LM Studio local model can process the sample PDFs end-to-end
- the watch queue runs one file at a time
- processed sample PDFs were archived to `watch/processed/`
- generated notes were written to `wiki/sources/`
- the worst `Related References` errors were eliminated
- extraction artifacts reported by lint are now zero for the sample run

---

## What Is Still Not Aligned or Still Incomplete

This section is the most important one. These are the areas where the project is still not where you expected it to be.

### 1. The repo still contains raw PDFs under `wiki/sources/`

This is currently the clearest structural mismatch.

Current reality:

- the repaired pipeline now expects raw files in `watch/`
- but the old sample PDFs are still sitting in `wiki/sources/`
- lint still flags them

Meaning:

- the code now enforces the right direction
- the workspace still contains old-state artifacts

### 2. Keyword enrichment is improved, but still not fully trustworthy

Current reality:

- the YAML noise is much lower than before
- but the enrichment logic is still rule-based and corpus-driven, not conceptually aware

Meaning:

- it can still produce topic-adjacent but weak `see also` or `tag` values
- it is safer, but not yet “scholarship-smart”

### 3. Concept-page creation was added late and may not match the ideal model yet

Current reality:

- concept pages are now auto-created for surviving `see also` links so lint can stay structurally consistent

Meaning:

- this solves broken links
- but it may create concept pages too eagerly compared with the final desired knowledge model

### 4. Related-reference extraction is still conservative, not complete

Current reality:

- the previous false positives were fixed
- but the current resolver is still not a full parser for scholarly references or in-text citation formats

Meaning:

- it is intentionally underpowered right now
- it avoids obvious garbage better than it captures all true citations

### 5. The quality of summaries still depends heavily on the local model

Current reality:

- notes are now structurally cleaner
- but summary/method/result quality still depends on what `gemma-4-e4b-it` produces from cleaned extraction

Meaning:

- the pipeline is more reliable structurally than semantically
- a stronger model or better staged prompting may still be needed for consistently high-quality literature notes

### 6. Fallback provider flow is only partially validated in practice

Current reality:

- fallback logic exists in code and tests
- cloud fallback was not fully exercised live in this repo session

Meaning:

- the feature exists
- but it should still be treated as partially implemented until real approval-gated fallback runs are tested end-to-end

### 7. The repo still mixes legacy and new workflow concepts

Current reality:

- this repo started as a bibliography/keyword linker
- it now also contains a literature wiki engine
- `config.yaml` and docs still reflect both worlds in places

Meaning:

- the product story is still split
- that split likely contributed to the mismatch between what you thought was being built and what actually got implemented

---

## What Remains To Be Done

This is the practical recovery plan from the current state.

### Immediate cleanup

1. Remove or relocate the raw PDFs still sitting in `wiki/sources/`.
2. Re-run lint to confirm the folder model is clean.
3. Decide whether the existing generated `_wiki` notes should be kept, regenerated, or discarded.

### Stabilization work

1. Tighten keyword enrichment again so only clearly topic-relevant concepts survive into YAML.
2. Refine concept-page creation so it reflects meaningful concepts rather than every surviving link target.
3. Improve publish gating with more content-quality heuristics, not just structural checks.

### Reference-resolution work

1. Add a stronger references-section parser.
2. Add support for more in-text citation forms:
   - `(Author, Year)`
   - `Author (Year)`
   - common multi-author variants
3. Only surface `Related References` when those matches are deterministic enough to trust.

### LLM-output quality work

1. Improve prompts for methods/results/data separation.
2. Consider a stronger summarization model for difficult items.
3. Add regression tests around live note quality characteristics where practical.

### Repo alignment work

1. Separate legacy linker docs from literature-wiki docs more clearly.
2. Clean up config overlap between the legacy toolchain and the wiki pipeline.
3. Decide whether this should remain one combined repo or be split into:
   - legacy bibliography linker
   - bibliography-first literature wiki

---

## Honest Summary of Current State

The project is not at the same point as the original high-level discussions implied.

What is true now:

- a substantial amount of the planned architecture exists
- several broken behaviors were found only after live runs
- some of those behaviors were repaired during implementation
- the repo now has a working bibliography-first ingest pipeline in code
- but the workflow, output semantics, and user expectations are still not fully aligned

The two biggest sources of mismatch appear to be:

1. The project evolved from a simple linker into a much more ambitious literature wiki, but the design contract did not stay explicit at every step.
2. Some parts were implemented “structurally first” and only later validated against real PDFs, which exposed poor extraction, noisy enrichment, and invalid reference logic.

That means the project is now in a better state than it was during the broken-output phase, but it still needs a deliberate alignment pass before it can be considered finished or trustworthy for large-scale use.

---

## Current Recommendation

Before adding any more features, the next work should focus on alignment and trust:

1. Clean the workspace so `watch/` is the only raw input area.
2. Decide whether the current generated notes are acceptable enough to keep as a base.
3. Run a smaller validation set of known-good PDFs and EPUBs.
4. Tighten keyword and concept semantics again based on those validation examples.
5. Only then resume work on fallback APIs, graph growth, or broader managed-wiki behavior.
