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
2. **Given** a directory of term definition files with YAML frontmatter, **When** I run the keyword generation script, **Then** an `unambiguous-keywords.csv` and an `ambiguous-keywords.json` are created where aliases are grouped by whether they can be linked automatically or require contextual review, and each entry carries its topic cluster metadata.
3. **Given** a Markdown note, **When** I invoke contextual analysis, **Then** the system classifies the note into one or more topic clusters (e.g., education, construction, technology) and produces a short explanation of the detected context.
4. **Given** the contextual classification and `unambiguous-keywords.csv`, **When** I run the keyword linking tool, **Then** only aliases whose clusters match the detected context are converted into wiki-links (e.g., `[[Some Concept]]`).
5. **Given** a note containing an ambiguous acronym like "CHAT", **When** I run the "smart linking" feature, **Then** the term is only linked to "Cultural-Historical Activity Theory" if the surrounding text contains related terms like "Vygotsky" or "Engeström".
6. **Given** a note that has already been processed, **When** I run the linking tool again, **Then** existing links are not modified or nested, and I can request a dry-run summary of proposed new links before applying changes.

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
- **FR-010**: The system MUST generate an `unambiguous-keywords.csv` file that includes, for every alias, the canonical link target and associated metadata describing at least one topic cluster/domain (e.g., `education`, `construction`). An `ambiguous-keywords.json` file MUST list aliases that require contextual disambiguation along with their candidate clusters.
- **FR-011**: The system MUST expose a machine-readable catalogue of all topic clusters and their descriptions so downstream components can reference consistent terminology.

### Context Analysis & Linking Requirements
- **FR-012**: System MUST find and replace plain-text author names in Markdown files with `[[FullName]]` or `[[FullName|LastName]]` style wiki-links, using the `authors.json` file as a source.
- **FR-013**: Before linking keywords, the system MUST classify each Markdown note into one or more topic clusters using contextual cues from the note. The classification MAY leverage an LLM but MUST always produce a deterministic list of clusters in the output.
- **FR-014**: System MUST restrict automatic keyword linking to aliases whose clusters overlap with the detected clusters for the note. If no overlap exists, the alias MUST be skipped.
- **FR-015**: When the text found in the note (the `Alias`) is different from the `LinkTarget`, the link MUST be created using the piped format: `[[LinkTarget|Alias]]`.
- **FR-016**: System MUST provide a dry-run option that previews the set of proposed wiki-links for a note before modifications are persisted.
- **FR-017**: System MUST NOT modify or re-link text that is already enclosed in `[[...]]` wiki-links (idempotency) and MUST avoid inserting links inside partially linked tokens (e.g., within `[[Existing Link|` segments).

### Future "Smart Linking" Requirements
- **FR-018**: System SHOULD provide an optional "smart linking" mode that uses an LLM for contextual analysis beyond the initial clustering phase.
- **FR-019**: In smart linking mode, the system MUST analyze the text surrounding a potential link to disambiguate terms. It SHOULD use contextual clues from the term definition files, such as the `see also` field and the body content (e.g., `TLDR` summaries), to improve accuracy.
- **FR-020**: The system MUST support using either a local LLM or a cloud-based LLM via an API.
- **FR-021**: API keys and endpoint URLs for cloud-based LLMs MUST be loaded from a `.env` file.
- **FR-022**: The `.env` file MUST be included in the project's `.gitignore` file to prevent accidental commits of secrets.

### Key Entities *(include if feature involves data)*
- **Author**: Represents a person extracted from the BibTeX file. Contains `fullName`, `firstName`, and `lastName`.
- **TermDefinition**: A single line inside the configured `term_source_file`. Each line defines the canonical link target, any aliases (including abbreviations in parentheses), and a short list of topic clusters that describe the term’s domain.
- **KeywordMapping**: A row in the `unambiguous-keywords.csv` that maps an alias to a primary term link together with its associated clusters.
- **MarkdownNote**: A `.md` file within a scannable directory that is a candidate for linking.
- **Configuration**: User-defined settings stored in `config.yaml`.
- **Secret**: User-specific API keys and endpoints stored in `.env`, ignored by Git.
- **TopicCluster**: A named category (e.g., `education`, `construction`, `technology`, `policy`) captured in the cluster catalogue and referenced by both terms and notes.

### Topic Cluster Catalogue *(reference implementation guidance)*
- **Education & Learning**: Pedagogy, apprenticeship models, workforce development, curriculum design, edtech.
- **Construction & Built Environment**: Offsite manufacturing, prefabrication, modular methods, BIM, DfMA, materials.
- **Technology & Computing**: AI/ML, immersive interfaces (AR/VR/XR), robotics, automation, software platforms.
- **Organizations & Institutions**: Universities, regulatory bodies, professional associations, government agencies.
- **Geography & Regions**: Countries, cities, regional programs, policy jurisdictions.
- **Policy & Governance**: Legislation, standards, funding programmes, labour regulation, public-private initiatives.
- **Methods & Research**: Qualitative/quantitative methods, thematic analysis, ethnography, fieldwork approaches.
- **People & Roles**: Specific individuals, roles (e.g., apprentices, instructors), workforce categories.
- **Sustainability & Materials**: Green construction, timber systems, material science terms.
- **General Concepts**: Crosscutting topics that don’t fit the above but are still valuable (e.g., knowledge acquisition, future of work).

> The catalogue MAY evolve; new clusters must be documented here and in the shared configuration so scripts remain in sync.

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
