import os
import re
import yaml
import csv

# --- Configuration ---
CONFIG_FILE = "config.yaml"

def load_config():
    """Loads configuration from the YAML file."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        return None

def load_keywords(filepath):
    """Loads keywords from a CSV file."""
    keywords = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip the header row
            for row in reader:
                if len(row) >= 2:
                    keywords.append({'search': row[0], 'replace': row[1]})
        
        # Sort keywords by the length of the search term, longest first.
        # This prevents "VR" from matching before "Mobile VR", for example.
        keywords.sort(key=lambda x: len(x['search']), reverse=True)
        return keywords
    except FileNotFoundError:
        print(f"Error: Keyword file not found at '{filepath}'")
        return []

def process_markdown_file(filepath, keywords):
    """
    Reads a markdown file, replaces keywords with Obsidian links, and saves it back.
    Returns True if the file was changed, False otherwise.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"  -> Could not read file: {e}")
        return False

    content = original_content

    for keyword in keywords:
        search_term = keyword['search']
        replacement_string = keyword['replace']
        
        # Regex to find the search term as a whole word, but not if it's already in [[...]]
        # The word boundary \b is crucial here.
        pattern = r'(?<!\[\[)\b' + re.escape(search_term) + r'\b(?!\||\]\])'
        
        # The replacement format is [[replacement_string]]
        replacement = f'[[{replacement_string}]]'
        
        content = re.sub(pattern, replacement, content)
        
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  -> Could not write to file: {e}")
            return False
            
    return False

def main():
    """Main function to orchestrate the keyword linking process."""
    print("Starting keyword linking process...")
    
    config = load_config()
    if not config:
        return

    scan_directories = config.get('scan_directories', [])
    keywords_file = config.get('keywords_csv_file')

    if not scan_directories or not keywords_file:
        print("Error: 'scan_directories' or 'keywords_csv_file' not set in config.yaml. Exiting.")
        return

    keywords = load_keywords(keywords_file)
    if not keywords:
        print("No keywords loaded. Exiting.")
        return
        
    print(f"Loaded {len(keywords)} keywords. Scanning directories...")
    
    modified_files_count = 0
    total_files_scanned = 0

    for directory in scan_directories:
        if not os.path.isdir(directory):
            print(f"\nWarning: Directory not found, skipping: {directory}")
            continue
            
        print(f"\nScanning directory: {directory}")
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.md'):
                    total_files_scanned += 1
                    filepath = os.path.join(root, filename)
                    print(f"- Processing: {filename}", end='')
                    if process_markdown_file(filepath, keywords):
                        modified_files_count += 1
                        print(" -> Linked!")
                    else:
                        print(" -> No changes.")
                        
    print("\n--- Process Complete ---")
    print(f"Scanned {total_files_scanned} Markdown files.")
    print(f"Modified {modified_files_count} files with new keyword links.")
    print("------------------------")


if __name__ == "__main__":
    main()