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

## Phase 5: Two-Stage & Smart Linking
*Goal: Implement ambiguity detection and a smart-linking fallback using an LLM.*

- [x] T029: Update `config.yaml` to replace `keywords_csv_file` with `unambiguous_keywords_csv` and add `ambiguous_keywords_json`.
- [x] T030: Modify `src/pkm_linker/generate_keywords.py` to detect ambiguous aliases and output two files: `unambiguous-keywords.csv` and `ambiguous-keywords.json`.
- [x] T031: Update `tests/test_generate_keywords.py` to assert that both the unambiguous and ambiguous output files are created correctly.
- [x] T032: Modify `src/pkm_linker/link_keywords.py` to read from `unambiguous-keywords.csv`.
- [x] T033: Add `openai` to `requirements.txt` and install it.
- [x] T034: Implement the core logic in `src/pkm_linker/smart_link.py` to read `ambiguous-keywords.json`, find terms in notes, and call the OpenAI API for contextual analysis.
- [x] T035: Add a new `--smart-link` flag to `main.py` that triggers the `smart_link.py` script.
- [x] T036: Update the `--all` command in `main.py` to run the smart linker after the simple linker.

### Phase 5 Checkpoint
- [ ] T037: Create session worklog in `logs/worklog_YYYY-MM-DD_s6.md`.
- [ ] T038: Commit all staged changes with the message "feat: Implement two-stage smart linking system".
- [ ] T039: Push the changes to the remote repository.
