import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from pkm_linker.create_author_json import main as run_create_author_json
from pkm_linker.link_authors import main as run_link_authors
from pkm_linker.link_keywords import main as run_link_keywords
from pkm_linker.generate_keywords import generate_keyword_mappings

def main():
    parser = argparse.ArgumentParser(description="A tool for linking notes in a PKM system.")
    parser.add_argument('--generate-authors', action='store_true', help='Generate the authors.json file from the BibTeX file.')
    parser.add_argument('--generate-keywords', action='store_true', help='Generate the keyword-mapping.csv file from the term list.')
    parser.add_argument('--link-authors', action='store_true', help='Link author names in your Markdown notes.')
    parser.add_argument('--link-keywords', action='store_true', help='Link keywords in your Markdown notes.')
    parser.add_argument('--all', action='store_true', help='Run all processing steps in order.')

    args = parser.parse_args()

    if args.all:
        print("Running all processing steps...")
        run_create_author_json()
        # In a real run, you would get the paths from config
        # For now, we assume default paths for the new function
        print("Generating keyword mappings...")
        generate_keyword_mappings('_helper/parent-list-terms_2025-10-08_155312.md', 'keyword-mapping.csv')
        print("Keyword mapping generation complete.")
        run_link_authors()
        run_link_keywords()
        print("All steps completed.")
    else:
        if args.generate_authors:
            run_create_author_json()
        if args.generate_keywords:
            print("Generating keyword mappings...")
            # This should also be driven by a config file in a future step
            generate_keyword_mappings('_helper/parent-list-terms_2025-10-08_155312.md', 'keyword-mapping.csv')
            print("Keyword mapping generation complete.")
        if args.link_authors:
            run_link_authors()
        if args.link_keywords:
            run_link_keywords()

if __name__ == '__main__':
    main()