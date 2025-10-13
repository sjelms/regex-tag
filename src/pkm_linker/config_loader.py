from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None

CONFIG_FILE = "config.yaml"


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _fallback_parse(content: str) -> Dict[str, Any]:
    """
    Minimal parser that understands the limited YAML subset used in config.yaml.
    Supports string values and top-level lists defined with "- item" syntax.
    """
    config: Dict[str, Any] = {}
    current_list_key: Optional[str] = None

    for raw_line in content.splitlines():
        line = raw_line.split('#', 1)[0].rstrip()
        if not line.strip():
            continue

        if line.lstrip().startswith('- '):
            if not current_list_key:
                raise ValueError(f"List item without a key in config: '{raw_line}'")
            item = _strip_quotes(line.lstrip()[2:].strip())
            config.setdefault(current_list_key, []).append(item)
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value:
                config[key] = _strip_quotes(value)
                current_list_key = None
            else:
                config[key] = []
                current_list_key = key
            continue

        raise ValueError(f"Unable to parse config line: '{raw_line}'")

    return config


def load_config(config_file: str = CONFIG_FILE) -> Optional[Dict[str, Any]]:
    """Loads configuration from the YAML file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if yaml:
                return yaml.safe_load(content)
            return _fallback_parse(content)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        return None
    except ValueError as exc:
        print(f"Error parsing configuration file '{config_file}': {exc}")
        return None
