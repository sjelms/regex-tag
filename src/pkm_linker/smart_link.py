from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency missing
    def load_dotenv() -> bool:
        return False

from .config_loader import load_config

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None  # type: ignore[misc]

CONTEXT_WINDOW = 160
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass
class AmbiguousEntry:
    alias: str
    candidates: List[str]
    source_terms: List[str]


def get_llm_api_key(service_name: str) -> Optional[str]:
    """
    Load an API key for a given LLM service from environment variables.

    Environment variables are populated from a .env file if present.
    Keys must follow the pattern "<SERVICE>_API_KEY".
    """
    load_dotenv()

    key_name = f"{service_name.upper()}_API_KEY"
    api_key = os.getenv(key_name)

    if not api_key:
        print(f"Warning: API key for {service_name} not found. Set '{key_name}' in your environment or .env file.")
        return None

    return api_key


def _load_ambiguous_entries(file_path: str) -> List[AmbiguousEntry]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_entries = json.load(f)
    except FileNotFoundError:
        print(f"Error: Ambiguous keyword file '{file_path}' not found.")
        return []
    except json.JSONDecodeError as exc:
        print(f"Error: Could not parse ambiguous keyword file '{file_path}': {exc}")
        return []

    entries: List[AmbiguousEntry] = []
    for entry in raw_entries:
        alias = entry.get("alias")
        candidates = entry.get("candidates") or []
        if not alias or len(candidates) < 2:
            # Skip malformed entries; they are either unhelpful or already unambiguous.
            continue
        entries.append(
            AmbiguousEntry(
                alias=alias,
                candidates=list(dict.fromkeys(candidates)),  # Preserve order, drop duplicates.
                source_terms=entry.get("source_terms") or [],
            )
        )

    return entries


def _extract_context(content: str, start: int, end: int, window: int = CONTEXT_WINDOW) -> str:
    slice_start = max(0, start - window)
    slice_end = min(len(content), end + window)
    return content[slice_start:slice_end]


def _build_alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    return re.compile(rf'(?<!\[\[)(?<!\|)\b{escaped}\b(?![\|\]])', re.IGNORECASE)


def _create_openai_client(api_key: str) -> Optional[OpenAI]:
    if OpenAI is None:
        print("Error: The 'openai' package is not installed. Install it with 'pip install openai'.")
        return None

    return OpenAI(api_key=api_key)


def _normalise_choice(choice: str, candidates: Iterable[str]) -> Optional[str]:
    if not choice:
        return None

    choice = choice.strip()
    if not choice:
        return None

    if choice.upper() == "NONE":
        return None

    for candidate in candidates:
        if candidate == choice:
            return candidate
        if candidate.lower() == choice.lower():
            return candidate

    return None


def _analyse_with_llm(
    client: OpenAI,
    model: str,
    alias: str,
    candidates: List[str],
    source_terms: List[str],
    context: str,
) -> Optional[str]:
    payload = {
        "alias": alias,
        "candidates": candidates,
        "source_terms": source_terms,
        "context": context.strip(),
    }

    prompt = (
        "You are helping to disambiguate wiki-link targets in a personal knowledge base.\n"
        "Select the most appropriate link target from the provided candidates based on the surrounding context.\n"
        "If none of the candidates fit, respond with the word NONE.\n"
        "Respond in JSON format: {\"link_target\": \"<candidate or NONE>\"}.\n"
        f"Input data:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are an assistant that returns strict JSON responses."},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:
        print(f"  -> LLM request failed: {exc}")
        return None

    try:
        message = response.choices[0].message.content if response.choices else None
        if not message:
            return None

        message = message.strip()
        result = json.loads(message)
        choice = result.get("link_target", "")
    except (json.JSONDecodeError, AttributeError, IndexError):
        # Fall back to interpreting the first line of the response.
        choice = (message or "").splitlines()[0] if message else ""

    return _normalise_choice(choice, candidates)


def _create_analyser(client: Optional[OpenAI], model: str) -> Optional[Callable[[AmbiguousEntry, str], Optional[str]]]:
    if client is None:
        return None

    analysis_cache: Dict[Tuple[str, str], Optional[str]] = {}

    def analyse(entry: AmbiguousEntry, context: str) -> Optional[str]:
        cache_key = (entry.alias.lower(), context.strip().lower())
        if cache_key in analysis_cache:
            return analysis_cache[cache_key]

        result = _analyse_with_llm(client, model, entry.alias, entry.candidates, entry.source_terms, context)
        analysis_cache[cache_key] = result
        return result

    return analyse


def _apply_ambiguous_entry(
    content: str,
    entry: AmbiguousEntry,
    analyser: Callable[[AmbiguousEntry, str], Optional[str]],
) -> Tuple[str, bool]:
    pattern = _build_alias_pattern(entry.alias)
    matches = list(pattern.finditer(content))
    if not matches:
        return content, False

    modified = False
    updated_segments: List[str] = []
    last_index = 0

    for match in matches:
        start, end = match.span()
        context = _extract_context(content, start, end)
        chosen_target = analyser(entry, context) if analyser else None

        updated_segments.append(content[last_index:start])

        if chosen_target:
            found_text = match.group(0)
            if found_text.lower() == chosen_target.lower():
                replacement = f"[[{chosen_target}]]"
            else:
                replacement = f"[[{chosen_target}|{found_text}]]"
            updated_segments.append(replacement)
            modified = True
        else:
            updated_segments.append(content[start:end])

        last_index = end

    updated_segments.append(content[last_index:])
    return "".join(updated_segments), modified


def run_smart_linking() -> None:
    """Entry point for the smart linking pipeline."""
    print("Starting smart linking process...")

    config = load_config()
    if not config:
        return

    scan_directories = config.get("scan_directories", [])
    ambiguous_file = config.get("ambiguous_keywords_json")

    if not scan_directories or not ambiguous_file:
        print("Error: 'scan_directories' or 'ambiguous_keywords_json' not set in config.yaml. Exiting.")
        return

    entries = _load_ambiguous_entries(ambiguous_file)
    if not entries:
        print("No ambiguous keywords to process.")
        return

    api_key = get_llm_api_key("openai")
    if not api_key:
        print("Skipping smart linking because no API key is available.")
        return

    client = _create_openai_client(api_key)
    if client is None:
        return

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    analyser = _create_analyser(client, model)
    if analyser is None:
        return

    total_modified = 0
    total_scanned = 0

    for directory in scan_directories:
        if not os.path.isdir(directory):
            print(f"\nWarning: Directory not found, skipping: {directory}")
            continue

        print(f"\nScanning directory (smart link): {directory}")
        for root, _, files in os.walk(directory):
            for filename in files:
                if not filename.endswith(".md"):
                    continue

                filepath = os.path.join(root, filename)
                total_scanned += 1

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as exc:
                    print(f"- {filename}: unable to read file ({exc})")
                    continue

                updated_content = content
                file_modified = False

                for entry in entries:
                    updated_content, entry_modified = _apply_ambiguous_entry(updated_content, entry, analyser)
                    if entry_modified:
                        file_modified = True

                if file_modified:
                    try:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(updated_content)
                        print(f"- {filename}: contextual links added.")
                        total_modified += 1
                    except Exception as exc:
                        print(f"- {filename}: unable to write updated file ({exc})")
                else:
                    print(f"- {filename}: no contextual links added.")

    print("\n--- Smart Linking Complete ---")
    print(f"Scanned {total_scanned} Markdown files for ambiguous aliases.")
    print(f"Modified {total_modified} files with contextual links.")
    print("------------------------------")


if __name__ == "__main__":
    run_smart_linking()
