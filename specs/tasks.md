# Tasks: Automated PKM Linking

**Input**: Design documents from `/specs/`

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions.

---

## Phase 1: Setup & Project Structure
*Goal: Prepare the project for the new keyword generation feature and improve the overall structure.*

- [ ] T001: Create directory `src/pkm_linker/`.
- [ ] T002: Add `python-frontmatter` and `python-dotenv` to `requirements.txt`.
- [ ] T003: Create a `.env.example` file in the root directory with placeholder content for future LLM API keys.
- [ ] T004: In `config.yaml`, add a new key `term_source_directory:` with a placeholder path.

### Phase 1 Checkpoint
- [ ] T005: Create session worklog in `logs/worklog_YYYY-MM-DD_s2.md`.
- [ ] T006: Commit all staged changes with the message "feat: Set up project structure for keyword generation".
- [ ] T007: Push the changes to the remote repository.

---

## Phase 2: Tests First (TDD)
*Goal: Write a failing test for the keyword generation feature before implementing it.*

- [ ] T008: Create new test file `tests/test_generate_keywords.py`.
- [ ] T009: In `tests/test_generate_keywords.py`, write a test that creates a temporary directory with mock `.md` term files (including YAML frontmatter) and asserts that a `keyword-mapping.csv` is generated with the correct content. This test MUST fail before proceeding.

### Phase 2 Checkpoint
- [ ] T010: Create session worklog in `logs/worklog_YYYY-MM-DD_s3.md`.
- [ ] T011: Commit all staged changes with the message "test: Add failing test for keyword generation".
- [ ] T012: Push the changes to the remote repository.

---

## Phase 3: Core Implementation & Refactoring
*Goal: Implement the keyword generation script and refactor the project into the new `src` structure.*

- [ ] T013: Create the script `src/pkm_linker/generate_keywords.py`.
- [ ] T014: Implement the keyword generation logic in `src/pkm_linker/generate_keywords.py` to make the test from T009 pass.
- [ ] T015: [P] Move `create_author_json.py` to `src/pkm_linker/create_author_json.py`.
- [ ] T016: [P] Move `link_authors.py` to `src/pkm_linker/link_authors.py`.
- [ ] T017: [P] Move `link_keywords.py` to `src/pkm_linker/link_keywords.py`.
- [ ] T018: Update `main.py` to import all modules from their new locations within `src/pkm_linker/`.
- [ ] T019: In `main.py`, add the `--generate-keywords` argument and wire it up to call the new `generate_keywords` function.

### Phase 3 Checkpoint
- [ ] T020: Create session worklog in `logs/worklog_YYYY-MM-DD_s4.md`.
- [ ] T021: Commit all staged changes with the message "feat: Implement keyword generation and refactor project structure".
- [ ] T022: Push the changes to the remote repository.

---

## Phase 4: Polish & Documentation
*Goal: Clean up the new code and document the new functionality for users.*

- [ ] T023: [P] Add docstrings and type hinting to `src/pkm_linker/generate_keywords.py`.
- [ ] T024: [P] Update `README.md` to document the new automatic keyword generation workflow and the `--generate-keywords` flag.
- [ ] T025: [P] Create a placeholder module `src/pkm_linker/smart_link.py` for future LLM logic, including a function to load secrets from a `.env` file.

### Phase 4 Checkpoint
- [ ] T026: Create session worklog in `logs/worklog_YYYY-MM-DD_s5.md`.
- [ ] T027: Commit all staged changes with the message "docs: Update documentation and add placeholder for smart linking".
- [ ] T028: Push the changes to the remote repository.
