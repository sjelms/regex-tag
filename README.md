# BibTeX to PKM Converter

This project provides a Python-based utility to automatically create a network of connections within your Personal Knowledge Management (PKM) system, such as Obsidian. The pipeline works in two stages: 
1. it parses a master BibTeX file to generate a clean, structured `authors.json` file. 
2. it uses this JSON file to scan your existing Markdown notes, finding plain-text mentions of authors and converting them into wiki-links (e.g., `John Smith` becomes `[[John Smith]]`) and surname alias links (e.g., `Smith` becomes `[[John Smith|Smith]]`). This retroactively links your notes to your academic sources, creating a densely interconnected knowledge base.

---

## ✨ Features

-   **Intelligent Author Linking**: A dedicated script scans your existing Markdown notes and automatically converts plain-text author names into wiki-links (e.g., `John Smith` becomes `[[John Smith]]` and `Smith` becomes `[[John Smith|Smith]]`).
-   **Configurable & Extensible**: Uses a `config.yaml` file to easily define which note directories to scan for author linking.
-   **Author Data Export**: Includes a utility to generate a clean, sorted `authors.json` file from your BibTeX library, which can be used by other tools or for data analysis.

---

## ⚙️ The Processing Pipeline

The workflow is designed as a multi-step pipeline. You can run the scripts in sequence to take your references from a single `.bib` file to a fully integrated part of your knowledge base.

1.  **Maintain `regex-tag.bib`: This is your single source of truth. All your academic references should be managed here, preferably using a tool like Zotero with the Better BibTeX plugin for easy export.
2.  **Generate `authors.json` (`create_author_json.py`)**: This script parses your `regex-tag.bib` file and creates a clean, unique, and alphabetized list of all authors. This JSON file acts as a master list for the other scripts.
3.  **Link Authors in Your Vault (`link_authors.py`)**: This final script uses the `authors.json` master list to scan your personal note directories (defined in `config.yaml`). It finds mentions of authors and intelligently converts them into the correct wiki-links, connecting your thoughts directly to the source material.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.8+
-   A BibTeX management tool (e.g., Zotero) to maintain your `regex-tag.bib` file.

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Set up a Virtual Environment** (Recommended)
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**
    You will need to create a `requirements.txt` file.

    **`requirements.txt`:**
    ```
    bibtexparser==1.4.3
    PyYAML==6.0.2
    ```
    Then, install the packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Project**
    -   **BibTeX File**: Place your BibTeX file in the root of the project and ensure it is named `regex-tag.bib`. If you use a different name, update the `BIBTEX_INPUT_FILE` variable in `create_author_json.py` and `convert_bibtex.py`.
    -   **Directories to Scan**: Open `config.yaml` and replace the placeholder paths with the **full paths** to the directories in your PKM vault that you want the linking script to process.

---

## Usage

Run the scripts from the terminal in the project's root directory.

1.  **Update the Author List** (Run this whenever you add new authors to your `.bib` file)
    ```bash
    python create_author_json.py
    ```

2.  **Generate/Update the Markdown Notes** (Run this to create or update notes from your `.bib` file)
    ```bash
    python convert_bibtex.py
    ```

3.  **Link Authors in Your Vault** (Run this to link authors in your other notes)
    ```bash
    python link_authors.py
    ```

---

## ⚠️ Important Notes

-   **Backup Your Vault!** The `link_authors.py` script modifies your Markdown files in place. It is **highly recommended** that you back up your notes or use a version control system like Git before running it.
-   **Surname Ambiguity**: The linking script cannot distinguish between two different authors who share the same last name. For example, if you have authors `John Smith` and `Jane Smith`, a mention of `Smith` will be linked to whichever author appears first in the `authors.json` file. These rare cases will require manual correction.
-   **Idempotency**: The scripts are designed to be safely run multiple times. The `link_authors.py` script will not re-link text that is already inside `[[...]]` brackets.