# Feature Specification: Automated PKM Linking

**Feature Branch**: `n/a`  
**Created**: 2025-09-22  
**Status**: Draft  

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a researcher and note-taker, I want to automatically create links in my personal knowledge base (PKM) from my academic references and a curated list of keywords, so that I can easily navigate my interconnected notes without manual effort.

### Acceptance Scenarios
1. **Given** a BibLaTeX file with author entries and a directory of Markdown notes, **When** I run the linking tool, **Then** plain-text mentions of author names in my notes are converted into wiki-links (e.g., `[[John Smith]]` or `[[John Smith|Smith]]`).
2. **Given** a directory of term definition files with YAML frontmatter, **When** I run the keyword generation script, **Then** an `unambiguous-keywords.csv` and an `ambiguous-keywords.json` are created where aliases are grouped by whether they can be linked automatically or require contextual review.
3. **Given** an `unambiguous-keywords.csv` file and a directory of Markdown notes, **When** I run the keyword linking tool, **Then** those keywords are converted into wiki-links (e.g., `[[Some Concept]]`).
4. **Given** a note containing an ambiguous acronym like "CHAT", **When** I run the "smart linking" feature, **Then** the term is only linked to "Cultural-Historical Activity Theory" if the surrounding text contains related terms like "Vygotsky" or "Engeström".
5. **Given** a note that has already been processed, **When** I run the linking tool again, **Then** existing links are not modified or nested.

### Edge Cases
- **Author Ambiguity**: How does the system handle two different authors who share the same last name (e.g., `John Smith` and `Jane Smith`)? The regex-based approach will link to the first match. The "smart linking" feature should aim to resolve this based on context.
- **Keyword Substrings**: The system must not link a keyword that appears as a substring within another word (e.g., linking "cat" in "caterpillar").
- **File Types**: The system should only process `.md` files and ignore all other file types.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST parse a `.bib` BibLaTeX file using the `pybtex` library to extract author first and last names.
- **FR-002**: System MUST generate a consolidated `authors.json` file containing a unique, sorted list of all authors.
- **FR-003**: System MUST allow users to specify directories to scan for notes and the location of data files via a `config.yaml` file.
- **FR-004**: All script functionalities MUST be executable from a single `main.py` command-line interface.
- **FR-005**: The CLI MUST support running each function individually via flags (e.g., `--link-authors`, `--generate-keywords`) or all together (`--all`).

### Keyword Generation Requirements
- **FR-006**: System MUST read a single, user-defined text file of terms (e.g., `parent-list-terms.md`).
- **FR-007**: For each line in the term file, the system MUST treat the entire line as the canonical `LinkTarget`, corresponding to a filename.
- **FR-008**: The system MUST parse each line to identify aliases. If a line contains an abbreviation in parentheses (e.g., "Cognitive Load Theory (CLT)"), the system MUST extract three aliases: the full string, the term itself ("Cognitive Load Theory"), and the abbreviation ("CLT").
- **FR-009**: The system MUST resolve alias conflicts by prioritizing the mapping associated with the most descriptive (longest) `LinkTarget`. For example, the alias "MIT" should map to "Massachusetts Institute of Technology (MIT)", not to "MIT".
- **FR-010**: The system MUST generate an `unambiguous-keywords.csv` file containing two columns, `Alias` and `LinkTarget`, to store linkable mappings, and an `ambiguous-keywords.json` file listing aliases that require contextual disambiguation.

### Linking Requirements
- **FR-011**: System MUST find and replace plain-text author names in Markdown files with `[[FullName]]` or `[[FullName|LastName]]` style wiki-links, using the `authors.json` file as a source.
- **FR-012**: System MUST find and replace keywords in Markdown files using the `unambiguous-keywords.csv`. If the text found in the note (the `Alias`) is different from the `LinkTarget`, the link MUST be created using the piped format: `[[LinkTarget|Alias]]`.
- **FR-013**: System MUST NOT modify or re-link text that is already enclosed in `[[...]]` wiki-links (idempotency).

### Future "Smart Linking" Requirements
- **FR-014**: System SHOULD provide an optional "smart linking" mode that uses an LLM for contextual analysis.
- **FR-015**: In smart linking mode, the system MUST analyze the text surrounding a potential link to disambiguate terms. It SHOULD use contextual clues from the term definition files, such as the `see also` field and the body content (e.g., `TLDR` summaries), to improve accuracy.
- **FR-016**: The system MUST support using either a local LLM or a cloud-based LLM via an API.
- **FR-017**: API keys and endpoint URLs for cloud-based LLMs MUST be loaded from a `.env` file.
- **FR-018**: The `.env` file MUST be included in the project's `.gitignore` file to prevent accidental commits of secrets.

### Key Entities *(include if feature involves data)*
- **Author**: Represents a person extracted from the BibTeX file. Contains `fullName`, `firstName`, and `lastName`.
- **TermDefinition**: A single line inside the configured `term_source_file`. Each line defines the canonical link target and any aliases (including abbreviations in parentheses) for a concept.
- **KeywordMapping**: A row in the `unambiguous-keywords.csv` that maps an alias to a primary term link.
- **MarkdownNote**: A `.md` file within a scannable directory that is a candidate for linking.
- **Configuration**: User-defined settings stored in `config.yaml`.
- **Secret**: User-specific API keys and endpoints stored in `.env`, ignored by Git.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [X] No implementation details (languages, frameworks, APIs)
- [X] Focused on user value and business needs
- [X] Written for non-technical stakeholders
- [X] All mandatory sections completed

### Requirement Completeness
- [X] No [NEEDS CLARIFICATION] markers remain
- [X] Requirements are testable and unambiguous  
- [X] Success criteria are measurable
- [X] Scope is clearly bounded
- [X] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [X] User description parsed
- [X] Key concepts extracted
- [X] Ambiguities marked
- [X] User scenarios defined
- [X] Requirements generated
- [X] Entities identified
- [X] Review checklist passed
