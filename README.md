# BibLaTeX to PKM Converter

This project provides a Python-based utility to automatically create a network of connections within your Personal Knowledge Management (PKM) system, such as Obsidian. The pipeline works in multiple stages:
1.  It parses a master BibLaTeX file to generate a clean, structured `authors.json` file.
2.  It generates an `unambiguous-keywords.csv` (and companion `ambiguous-keywords.json`) from a simple text file of your key terms and their aliases.
3.  It uses these generated files to scan your existing Markdown notes, finding plain-text mentions and converting them into wiki-links (e.g., `John Smith` becomes `[[John Smith]]` or `CLT` becomes `[[Cognitive Load Theory (CLT)|CLT]]`).

This retroactively links your notes to your academic sources and key concepts, creating a densely interconnected knowledge base.

---

## ✨ Features

-   **CLI Control**: A single `main.py` entrypoint with flags (`--generate-authors`, `--generate-keywords`, `--link-authors`, etc.) to control the entire pipeline.
-   **Intelligent Author Linking**: Converts author names into wiki-links, including surname aliases (e.g., `Smith` becomes `[[John Smith|Smith]]`).
-   **Automatic Keyword & Alias Linking**: Parses a simple list of terms and automatically handles abbreviations in parentheses (e.g., `Cognitive Load Theory (CLT)`). It then finds and links both the full term and the alias, creating piped links where necessary.
-   **Configurable**: Uses a `config.yaml` file to easily define which note directories to scan.
-   **Safe & Idempotent**: The linking scripts will not re-link text that is already inside `[[...]]` brackets, so they can be run multiple times safely.

### How Keyword Linking Works

Stage 1 produces `unambiguous-keywords.csv`, a dictionary with two columns: `Alias` and `LinkTarget`.

-   **`LinkTarget`**: This is always the full, canonical name of the note file (e.g., `Cognitive Load Theory (CLT)`).
-   **`Alias`**: This is a term that should be linked (e.g., `CLT` or `Cognitive Load Theory`).

When the script finds an `Alias` in your text, it looks up its `LinkTarget`. If they are different, it creates a piped link: `[[LinkTarget|Alias]]`. This ensures the link is correct while preserving the original text.

Stage 2 produces `ambiguous-keywords.json`, a list of aliases that map to multiple possible link targets. The optional `--smart-link` command invokes an LLM to examine each occurrence in context and choose the correct target before adding a wiki-link.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.13+
-   A BibTeX management tool (e.g., Zotero) to maintain your `.bib` file.

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Set up a Virtual Environment** (Recommended)
    ```bash
    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Project**
    -   Copy `config.example.yaml` to `config.yaml`.
    -   Update `config.yaml` with the absolute path to your notes directory (`scan_directories`).
    -   Place your BibLaTeX file (e.g., `regex-tag.bib`) in the root of the project.
    -   Create a text file containing your list of keywords, one per line. Update `term_source_file` in `config.yaml` to point to this file.

---

## Usage

All commands are run through `main.py` from the project's root directory.

```bash
# View all available commands
python main.py --help
```

### Recommended Workflow

1.  **Generate Authors** (Run this whenever you add new authors to your `.bib` file)
    ```bash
    python main.py --generate-authors
    ```

2.  **Generate Keywords** (Run this when you update your term list)
    ```bash
    python main.py --generate-keywords
    ```

3.  **Link Authors & Keywords** (Run this to link everything in your vault)
    ```bash
    python main.py --link-authors
    python main.py --link-keywords
    ```

4.  **Smart Link Ambiguous Terms** (Optional, requires an API key in `.env`)
    ```bash
    python main.py --smart-link
    ```

5.  **Run All Steps** (A convenient way to do everything at once, including smart linking if configured)
    ```bash
    python main.py --all
    ```

---

## ⚠️ Important Notes

-   **Backup Your Vault!** The linking scripts modify your Markdown files in place. It is **highly recommended** that you back up your notes or use a version control system like Git before running them.
-   **Surname Ambiguity**: The author linking script cannot distinguish between two different authors who share the same last name. These rare cases may require manual correction.
