from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    repo_root: Path
    bibliography_file: Path
    template_file: Path
    cache_dir: Path
    raw_dir: Path
    extracted_dir: Path
    wiki_dir: Path
    wiki_sources_dir: Path
    graph_dir: Path
    watch_dir: Path
    processed_dir: Path
    other_dir: Path
    registry_file: Path
    bibliography_registry_file: Path
    local_config_file: Path
    env_file: Path
    provider_backend: str
    provider_model: str
    provider_api_base: str
    provider_api_key_env: str
    provider_timeout_seconds: int
    show_completion_dialog: bool


def _read_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle.read()) or {}


def load_config(repo_root: Path | None = None) -> AppConfig:
    root = repo_root or Path.cwd()
    config_path = root / "config.yaml"
    local_config_path = root / "config.local.yaml"
    config_data = _read_yaml_if_exists(config_path)
    local_data = _read_yaml_if_exists(local_config_path)
    merged = {**config_data, **local_data}

    provider = {**(merged.get("provider") or {})}

    bibliography_file = root / merged.get("bibliography_file", "regex-tag.bib")
    template_file = root / merged.get("template_file", "specs/lit-note-template.md")
    cache_dir = root / merged.get("cache_dir", "cache")
    raw_dir = root / merged.get("raw_dir", "raw")
    extracted_dir = root / merged.get("extracted_dir", "extracted")
    wiki_dir = root / merged.get("wiki_dir", "wiki")
    graph_dir = root / merged.get("graph_dir", "graph")
    watch_dir = root / merged.get("watch_dir", "watch")
    processed_dir = watch_dir / merged.get("processed_subdir", "processed")
    other_dir = watch_dir / merged.get("other_subdir", "other")

    return AppConfig(
        repo_root=root,
        bibliography_file=bibliography_file,
        template_file=template_file,
        cache_dir=cache_dir,
        raw_dir=raw_dir,
        extracted_dir=extracted_dir,
        wiki_dir=wiki_dir,
        wiki_sources_dir=wiki_dir / "sources",
        graph_dir=graph_dir,
        watch_dir=watch_dir,
        processed_dir=processed_dir,
        other_dir=other_dir,
        registry_file=cache_dir / "source_registry.json",
        bibliography_registry_file=cache_dir / "bibliography_registry.json",
        local_config_file=local_config_path,
        env_file=root / ".env",
        provider_backend=provider.get("backend", os.getenv("LIT_WIKI_PROVIDER", "heuristic")),
        provider_model=provider.get("model", os.getenv("LIT_WIKI_MODEL", "gemma-4-e4b-it")),
        provider_api_base=provider.get("api_base", os.getenv("LIT_WIKI_API_BASE", "")),
        provider_api_key_env=provider.get("api_key_env", os.getenv("LIT_WIKI_API_KEY_ENV", "LIT_WIKI_API_KEY")),
        provider_timeout_seconds=int(provider.get("timeout_seconds", os.getenv("LIT_WIKI_TIMEOUT_SECONDS", "60"))),
        show_completion_dialog=bool(merged.get("show_completion_dialog", True)),
    )


def ensure_runtime_directories(config: AppConfig) -> None:
    for path in (
        config.cache_dir,
        config.raw_dir,
        config.extracted_dir,
        config.wiki_dir,
        config.wiki_sources_dir,
        config.graph_dir,
        config.watch_dir,
        config.processed_dir,
        config.other_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
