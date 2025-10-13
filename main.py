import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from pkm_linker.config_loader import load_config


def generate_keywords_step() -> bool:
    """Generate keyword mappings using configuration settings."""
    config = load_config()
    if not config:
        return False

    term_file = config.get('term_source_file')
    unambiguous_csv = config.get('unambiguous_keywords_csv')
    ambiguous_json = config.get('ambiguous_keywords_json')

    if not term_file or not unambiguous_csv or not ambiguous_json:
        print("Error: 'term_source_file', 'unambiguous_keywords_csv', or 'ambiguous_keywords_json' not set in config.yaml.")
        return False

    print("Generating keyword mappings...")
    from pkm_linker.generate_keywords import generate_keyword_mappings
    generate_keyword_mappings(term_file, unambiguous_csv, ambiguous_json)
    print("Keyword mapping generation complete.")
    return True


def main():
    parser = argparse.ArgumentParser(description="A tool for linking notes in a PKM system.")
    parser.add_argument('--generate-authors', action='store_true', help='Generate the authors.json file from the BibTeX file.')
    parser.add_argument('--generate-keywords', action='store_true', help='Generate the unambiguous and ambiguous keyword outputs from the term list.')
    parser.add_argument('--link-authors', action='store_true', help='Link author names in your Markdown notes.')
    parser.add_argument('--link-keywords', action='store_true', help='Link keywords in your Markdown notes.')
    parser.add_argument('--smart-link', action='store_true', help='Run contextual smart linking for ambiguous terms using an LLM.')
    parser.add_argument('--all', action='store_true', help='Run all processing steps in order.')

    args = parser.parse_args()

    if args.all:
        print("Running all processing steps...")
        try:
            from pkm_linker.create_author_json import main as run_create_author_json
            run_create_author_json()
        except ModuleNotFoundError as exc:
            print(f"Unable to run author JSON generation. Missing dependency: {exc.name}")
            return

        if not generate_keywords_step():
            return

        from pkm_linker.link_authors import main as run_link_authors
        run_link_authors()
        from pkm_linker.link_keywords import main as run_link_keywords
        run_link_keywords()
        from pkm_linker.smart_link import run_smart_linking
        run_smart_linking()
        print("All steps completed.")
        return

    if args.generate_authors:
        try:
            from pkm_linker.create_author_json import main as run_create_author_json
            run_create_author_json()
        except ModuleNotFoundError as exc:
            print(f"Unable to run author JSON generation. Missing dependency: {exc.name}")
            return

    if args.generate_keywords:
        if not generate_keywords_step():
            return

    if args.link_authors:
        from pkm_linker.link_authors import main as run_link_authors
        run_link_authors()

    if args.link_keywords:
        from pkm_linker.link_keywords import main as run_link_keywords
        run_link_keywords()

    if args.smart_link:
        from pkm_linker.smart_link import run_smart_linking
        run_smart_linking()


if __name__ == '__main__':
    main()
