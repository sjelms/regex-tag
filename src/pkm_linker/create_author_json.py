
import json
import re
from pybtex.database.input import bibtex
import latexcodec

# --- Configuration ---
BIBTEX_INPUT_FILE = "regex-tag.bib"
JSON_OUTPUT_FILE = "authors.json"

def process_author_name(person: "pybtex.database.Person") -> dict | None:
    """
    Cleans and processes a single author's name from a pybtex Person object.
    Returns a structured dictionary.
    """
    
    first_names = " ".join(person.first_names)
    middle_names = " ".join(person.middle_names)
    last_names = " ".join(person.last_names)
    
    # Combine names, handling potential multiple parts
    full_name_parts = [first_names, middle_names, last_names]
    full_name = " ".join(part for part in full_name_parts if part)

    if not full_name:
        return None

    return {
        "fullName": full_name,
        "firstName": " ".join([first_names, middle_names]).strip(),
        "lastName": last_names,
    }

def main():
    """
    Main function to parse the BibTeX file and generate the JSON output.
    """
    print(f"Reading BibTeX file: {BIBTEX_INPUT_FILE}")
    try:
        parser = bibtex.Parser()
        bib_database = parser.parse_file(BIBTEX_INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: The file '{BIBTEX_INPUT_FILE}' was not found.")
        print("Please make sure the script and the .bib file are in the same directory.")
        return

    unique_authors = {}

    for entry in bib_database.entries.values():
        persons = entry.persons.get('author') or entry.persons.get('editor')
        
        if not persons:
            continue

        for person in persons:
            processed_author = process_author_name(person)
            
            if processed_author:
                unique_authors[processed_author['fullName']] = processed_author

    author_list_final = list(unique_authors.values())
    author_list_final.sort(key=lambda x: x['fullName'])

    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as jsonfile:
        json.dump(author_list_final, jsonfile, indent=2, ensure_ascii=False)

    print(f"✅ Success! Wrote {len(author_list_final)} unique authors to '{JSON_OUTPUT_FILE}'")


if __name__ == "__main__":
    main()
