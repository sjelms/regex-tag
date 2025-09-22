
import argparse
from create_author_json import main as run_create_author_json
from link_authors import main as run_link_authors
from link_keywords import main as run_link_keywords

def main():
    parser = argparse.ArgumentParser(description="A tool for linking notes in a PKM system.")
    parser.add_argument('--generate-authors', action='store_true', help='Generate the authors.json file from the BibTeX file.')
    parser.add_argument('--link-authors', action='store_true', help='Link author names in your Markdown notes.')
    parser.add_argument('--link-keywords', action='store_true', help='Link keywords in your Markdown notes.')
    parser.add_argument('--all', action='store_true', help='Run all processing steps in order.')

    args = parser.parse_args()

    if args.all:
        print("Running all processing steps...")
        run_create_author_json()
        run_link_authors()
        run_link_keywords()
        print("All steps completed.")
    else:
        if args.generate_authors:
            run_create_author_json()
        if args.link_authors:
            run_link_authors()
        if args.link_keywords:
            run_link_keywords()

if __name__ == '__main__':
    main()
