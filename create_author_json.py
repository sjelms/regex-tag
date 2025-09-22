import bibtexparser
import json
import re

# --- Configuration ---
BIBTEX_INPUT_FILE = "regex-tag.bib"
JSON_OUTPUT_FILE = "authors.json"

def process_author_name(raw_name: str) -> dict | None:
    """
    Cleans and processes a single author's name into a structured dictionary.
    Handles 'Last, First' and 'First Last' formats.
    Returns None for institutional authors (those in curly braces).
    """
    name = re.sub(r'\s+', ' ', raw_name).strip()

    if name.startswith('{') and name.endswith('}'):
        return None

    if ',' in name:
        parts = name.split(',', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip()
        full_name = f"{first_name} {last_name}"
    else:
        full_name = name
    
    name_parts = full_name.split()
    if not name_parts:
        return None
        
    last_name = name_parts[-1]
    first_name = ' '.join(name_parts[:-1])

    return {
        "fullName": full_name,
        "firstName": first_name,
        "lastName": last_name,
    }

def main():
    """
    Main function to parse the BibTeX file and generate the JSON output.
    """
    print(f"Reading BibTeX file: {BIBTEX_INPUT_FILE}")
    try:
        with open(BIBTEX_INPUT_FILE, 'r', encoding='utf-8') as bibfile:
            bib_database = bibtexparser.load(bibfile)
    except FileNotFoundError:
        print(f"Error: The file '{BIBTEX_INPUT_FILE}' was not found.")
        print("Please make sure the script and the .bib file are in the same directory.")
        return

    unique_authors = {}

    for entry in bib_database.entries:
        author_string = entry.get('author') or entry.get('editor')
        
        if not author_string:
            continue
        
        # FIX: Normalize all whitespace (including newlines) to a single space.
        # This handles multi-line author fields in the .bib file correctly.
        author_string = " ".join(author_string.split())

        author_list = [author.strip() for author in author_string.split(' and ')]

        for raw_author_name in author_list:
            processed_author = process_author_name(raw_author_name)
            
            if processed_author:
                unique_authors[processed_author['fullName']] = processed_author

    author_list_final = list(unique_authors.values())
    author_list_final.sort(key=lambda x: x['fullName'])

    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as jsonfile:
        json.dump(author_list_final, jsonfile, indent=2, ensure_ascii=False)

    print(f"✅ Success! Wrote {len(author_list_final)} unique authors to '{JSON_OUTPUT_FILE}'")


if __name__ == "__main__":
    main()