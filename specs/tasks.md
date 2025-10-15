# Tasks: Automated PKM Linking

**Input**: Design documents from `/specs/`

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions.

---

## Phase 1: Setup & Project Structure
*Goal: Prepare the project for the new keyword generation feature and improve the overall structure.*

- [x] T001: Create directory `src/pkm_linker/`.
- [x] T002: Add `python-frontmatter` and `python-dotenv` to `requirements.txt`.
- [x] T003: Create a `.env.example` file in the root directory with LLM API key.
- [x] T004: In `config.yaml`, add a new key `term_source_file:` with a placeholder path.

### Phase 1 Checkpoint
- [x] T005: Create session worklog in `logs/worklog_YYYY-MM-DD_s2.md`.
- [x] T006: Commit all staged changes with the message "feat: Set up project structure for keyword generation".
- [x] T007: Push the changes to the remote repository.

---

## Phase 1.5: BibLaTeX Migration
*Goal: Update the project to use pybtex for parsing BibLaTeX files.*

- [x] T007a: Update `create_author_json.py` to use `pybtex` and `latexcodec` to parse the BibLaTeX file.
- [x] T007b: Ensure the author processing logic in `create_author_json.py` correctly handles the output from `pybtex`.

---

## Phase 2: Tests First (TDD)
*Goal: Write a failing test for the keyword generation feature before implementing it.*

- [x] T008: Create new test file `tests/test_generate_keywords.py`.
- [x] T009: In `tests/test_generate_keywords.py`, write a test that creates a temporary mock term file (e.g., with content like "Cognitive Load Theory (CLT)") and asserts that the unambiguous CSV and ambiguous JSON outputs contain the correct aliases and link targets. This test MUST fail before proceeding.

### Phase 2 Checkpoint
- [x] T010: Create session worklog in `logs/worklog_YYYY-MM-DD_s3.md`.
- [x] T011: Commit all staged changes with the message "test: Add failing test for keyword generation".
- [x] T012: Push the changes to the remote repository.

---

## Phase 3: Core Implementation & Refactoring
*Goal: Implement the keyword generation script and refactor the project into the new `src` structure.*

- [x] T013: Create the script `src/pkm_linker/generate_keywords.py`.
- [x] T014: Implement the keyword generation logic in `src/pkm_linker/generate_keywords.py` to make the test from T009 pass. The script must parse the single term file and handle aliases in parentheses.
- [x] T015: [P] Move `create_author_json.py` to `src/pkm_linker/create_author_json.py`.
- [x] T016: [P] Move `link_authors.py` to `src/pkm_linker/link_authors.py`.
- [x] T017: [P] Move `link_keywords.py` to `src/pkm_linker/link_keywords.py` and update it to handle the piped link format `[[LinkTarget|Alias]]` when an alias is found.
- [x] T018: Update `main.py` to import all modules from their new locations within `src/pkm_linker/`.
- [x] T019: In `main.py`, add the `--generate-keywords` argument and wire it up to call the new `generate_keywords` function.

### Phase 3 Checkpoint
- [x] T020: Create session worklog in `logs/worklog_YYYY-MM-DD_s4.md`.
- [x] T021: Commit all staged changes with the message "feat: Implement keyword generation and refactor project structure".
- [x] T022: Push the changes to the remote repository.

---

## Phase 4: Polish & Documentation
*Goal: Clean up the new code and document the new functionality for users.*

- [x] T023: [P] Add docstrings and type hinting to `src/pkm_linker/generate_keywords.py`.
- [x] T024: [P] Update `README.md` to document the new automatic keyword generation workflow and the `--generate-keywords` flag.
- [x] T025: [P] Create a placeholder module `src/pkm_linker/smart_link.py` for future LLM logic, including a function to load secrets from a `.env` file.

### Phase 4 Checkpoint
- [ ] T026: Create session worklog in `logs/worklog_YYYY-MM-DD_s5.md`.
- [ ] T027: Commit all staged changes with the message "docs: Update documentation and add placeholder for smart linking".
- [ ] T028: Push the changes to the remote repository.

---

## Phase 5: Context-Aware Pivot (Strategy & Taxonomy)
*Goal: Establish the metadata and process changes required for context-sensitive linking.*

- [ ] T029: Define and document the initial topic cluster taxonomy (e.g., `education`, `construction`, `technology`, `institutions`) in `specs/spec.md`.
- [ ] T030: Update the term source format and `unambiguous-keywords.csv` schema to include cluster/domain metadata for every entry.
- [ ] T031: Extend `src/pkm_linker/generate_keywords.py` so it populates the new metadata fields while still producing ambiguous/unambiguous outputs.
- [ ] T032: Augment `tests/test_generate_keywords.py` to verify that cluster metadata is written to the CSV and preserved in the JSON output.
- [ ] T033: Document the taxonomy and CSV changes in `README.md` and `config.example.yaml`.

### Phase 5 Checkpoint
- [ ] T034: Create session worklog in `logs/worklog_YYYY-MM-DD_s5.md`.
- [ ] T035: Commit all staged changes with the message "chore: add keyword clustering metadata".
- [ ] T036: Push the changes to the remote repository.

---

## Phase 6: Context Classification & Filtering
*Goal: Use note-level analysis (LLM-assisted) to select relevant clusters before linking.*

- [ ] T037: Design the context-classification prompt/contract and capture it in `specs/spec.md`.
- [ ] T038: Implement a lightweight classifier utility (`src/pkm_linker/context_classifier.py`) that returns clusters and confidence using an LLM or rule-based fallback.
- [ ] T039: Add configuration to `config.yaml` for classifier settings (e.g., max tokens, models, fallback behaviour).
- [ ] T040: Wire `main.py`/CLI to support a `--classify` dry-run command that prints detected clusters and justification.
- [ ] T041: Create unit/integration tests (or golden fixtures) validating classification outputs on at least two representative notes.

### Phase 6 Checkpoint
- [ ] T042: Create session worklog in `logs/worklog_YYYY-MM-DD_s6.md`.
- [ ] T043: Commit all staged changes with the message "feat: add context classification for linking".
- [ ] T044: Push the changes to the remote repository.

---

## Phase 7: Safe Linking & Dry-Run Workflow
*Goal: Apply filtered aliases with improved boundary checks and preview capabilities.*

- [ ] T045: Rework `src/pkm_linker/link_keywords.py` to accept a filtered alias set, enforce explicit boundary rules, and skip text already within wiki-links.
- [ ] T046: Implement a dry-run mode that lists proposed replacements (alias, target, line excerpt) without modifying files.
- [ ] T047: Add regression tests covering punctuation-heavy aliases (`expansive/restrictive continuum`) and ensure no double-linking occurs.
- [ ] T048: Update CLI help and `README.md` to describe the dry-run flow and safe-linking guarantees.

### Phase 7 Checkpoint
- [ ] T049: Create session worklog in `logs/worklog_YYYY-MM-DD_s7.md`.
- [ ] T050: Commit all staged changes with the message "feat: add safe link filtering and dry run".
- [ ] T051: Push the changes to the remote repository.

---

## Phase 8: Smart Linking Refinement
*Goal: Reintroduce LLM-based disambiguation leveraging the new clusters and context.*

- [ ] T052: Refactor `src/pkm_linker/smart_link.py` to consume cluster-aware ambiguous terms and the classifier output.
- [ ] T053: Implement caching and rate-limit handling for smart-link API calls; log outcomes for auditability.
- [ ] T054: Provide a report summarising ambiguous terms that were skipped or require manual review.
- [ ] T055: Add end-to-end tests (recorded mocks) ensuring smart linking only fires for cluster-aligned aliases.

### Phase 8 Checkpoint
- [ ] T056: Create session worklog in `logs/worklog_YYYY-MM-DD_s8.md`.
- [ ] T057: Commit all staged changes with the message "feat: integrate contextual smart linking".
- [ ] T058: Push the changes to the remote repository.

---

## Phase 9: Validation & Rollout
*Goal: Validate the full pipeline and capture operational guidance.*

- [ ] T059: Assemble a representative Markdown test suite (education, construction, tech notes) under `_helper/test/` for repeatable validation.
- [ ] T060: Document an end-to-end runbook covering classification, dry-run review, final linking, and smart-link reconciliation.
- [ ] T061: Capture before/after diffs for key notes and file them in `logs/validation/`.
- [ ] T062: Prepare a final summary worklog and changelog entry for release.

### Phase 9 Checkpoint
- [ ] T063: Create session worklog in `logs/worklog_YYYY-MM-DD_s9.md`.
- [ ] T064: Commit all staged changes with the message "chore: finalize contextual linking rollout".
- [ ] T065: Push the changes to the remote repository.
