# Gemini Code Assistant Context

## Project Overview

This project is a Python-based utility designed to enhance Personal Knowledge Management (PKM) systems like Obsidian. It automates the creation of a densely interconnected knowledge base by linking academic sources from a BibTeX file to Markdown notes. The core functionality involves parsing a `.bib` file to extract author data, and then using that data to find and replace author names with wiki-links in a specified set of Markdown files.

The project is built with Python and relies on the `bibtexparser` and `PyYAML` libraries. The architecture is script-based, with separate Python files for distinct stages of the processing pipeline. Configuration is managed through a `config.yaml` file, allowing users to easily specify the directories to be processed.

## Building and Running

This project does not have a traditional build process. The scripts are intended to be run directly from the command line.

### Prerequisites

*   Python 3.8+
*   A BibTeX file (defaulting to `regex-tag.bib`)

### Installation

1.  **Set up a virtual environment (recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Scripts

The scripts should be run in the following order:

1.  **Generate the author list:** This script parses the BibTeX file and creates `authors.json`.
    ```bash
    python create_author_json.py
    ```

2.  **Link authors in your notes:** This script scans the directories specified in `config.yaml` and links author names.
    ```bash
    python link_authors.py
    ```

## Development Conventions

*   **Configuration:** Project settings, such as the paths to the directories to be scanned, are defined in `config.yaml`.
*   **Data Management:** The master list of authors is stored in `authors.json`, which is generated from the BibTeX file.
*   **Modularity:** The project is divided into single-purpose scripts (`create_author_json.py`, `link_authors.py`, etc.) to create a clear and maintainable workflow.
*   **Idempotency:** The linking script is designed to be run multiple times without creating duplicate links. It will not re-link text that is already enclosed in `[[...]]`.
*   **Error Handling:** The scripts include basic error handling, such as checking for the existence of input files.

## Session Management

*   **Worklogs:** At the end of each session, or upon user request, generate a detailed worklog in the `/logs` directory. The log should summarize all actions, decisions, and changes made during the session. The filename should follow the format `worklog_YYYY-MM-DD_sN.md`.
