from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProviderSpec:
    name: str
    backend: str
    model: str
    api_base: str
    api_key_env: str
    timeout_seconds: int
    family: str = ""
    task_model: str = ""


@dataclass
class ModelFamily:
    name: str
    label: str
    provider: str
    task_models: dict[str, str] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)


@dataclass
class RetryPolicyConfig:
    local_max_attempts: int = 2


@dataclass
class ApprovalPolicyConfig:
    required: bool = True
    default_decision: str = "prompt"


@dataclass
class BudgetPolicyConfig:
    max_input_chars_per_request: int = 12000
    max_output_tokens_per_request: int = 1200
    max_requests_per_file: int = 4
    max_tokens_per_file: int = 12000
    max_tokens_per_day: int = 50000
    max_estimated_cost_per_file: float = 0.0
    max_estimated_cost_per_day: float = 0.0


@dataclass
class KeywordPolicyConfig:
    enabled: bool = False
    unambiguous_csv: Path | None = None
    ambiguous_json: Path | None = None
    mode: str = "guidance_enrichment"
    max_guidance_terms: int = 20
    max_see_also_links: int = 10


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
    budget_ledger_file: Path
    local_config_file: Path
    env_file: Path
    primary_provider: ProviderSpec
    model_families: dict[str, ModelFamily] = field(default_factory=dict)
    fallback_providers: list[ProviderSpec] = field(default_factory=list)
    retry_policy: RetryPolicyConfig = field(default_factory=RetryPolicyConfig)
    approval_policy: ApprovalPolicyConfig = field(default_factory=ApprovalPolicyConfig)
    budget_policy: BudgetPolicyConfig = field(default_factory=BudgetPolicyConfig)
    keyword_policy: KeywordPolicyConfig = field(default_factory=KeywordPolicyConfig)
    show_completion_dialog: bool = True


def _read_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle.read()) or {}


def _family_map(provider_payload: dict[str, Any]) -> dict[str, ModelFamily]:
    families: dict[str, ModelFamily] = {}
    for family_name, payload in (provider_payload.get("families") or {}).items():
        families[family_name] = ModelFamily(
            name=family_name,
            label=str(payload.get("label", family_name)),
            provider=str(payload.get("provider", "")),
            task_models=dict(payload.get("task_models") or {}),
            models=dict(payload.get("models") or {}),
        )
    return families


def _backend_from_provider_name(provider_name: str) -> str:
    lowered = provider_name.lower()
    if lowered == "google":
        return "gemini"
    return lowered


def _provider_spec_from_mapping(
    name: str,
    payload: dict[str, Any],
    families: dict[str, ModelFamily],
    env_prefix: str = "LIT_WIKI",
) -> ProviderSpec:
    family_name = str(payload.get("family", "")).strip()
    task_model = str(payload.get("task_model", "")).strip()
    family = families.get(family_name) if family_name else None
    backend = payload.get("backend")
    model = payload.get("model")
    if family is not None:
        backend = backend or _backend_from_provider_name(family.provider)
        if not model and task_model:
            model = family.task_models.get(task_model, "")
        if not model and family.task_models.get("default"):
            model = family.task_models["default"]
        if model and family.models:
            model = family.models.get(str(model), str(model))
    backend = backend or "heuristic"
    model = model or "gemma-4-e4b-it"
    api_key_env_default = f"{env_prefix}_{name.upper()}_API_KEY".replace("-", "_")
    return ProviderSpec(
        name=name,
        backend=backend,
        model=str(model),
        api_base=payload.get("api_base", os.getenv(f"{env_prefix}_{name.upper()}_API_BASE".replace("-", "_"), "")),
        api_key_env=payload.get("api_key_env", api_key_env_default),
        timeout_seconds=int(payload.get("timeout_seconds", 60)),
        family=family_name,
        task_model=task_model,
    )


def _fallback_specs(payloads: list[dict[str, Any]] | None, families: dict[str, ModelFamily]) -> list[ProviderSpec]:
    specs: list[ProviderSpec] = []
    for index, payload in enumerate(payloads or [], start=1):
        name = str(payload.get("name", f"fallback_{index}"))
        specs.append(_provider_spec_from_mapping(name, payload, families))
    return specs


def _keyword_policy(root: Path, merged: dict[str, Any]) -> KeywordPolicyConfig:
    payload = merged.get("keywords") or {}
    unambiguous_csv = payload.get("unambiguous_csv")
    ambiguous_json = payload.get("ambiguous_json")
    return KeywordPolicyConfig(
        enabled=bool(payload.get("enabled", False)),
        unambiguous_csv=(root / unambiguous_csv) if unambiguous_csv else None,
        ambiguous_json=(root / ambiguous_json) if ambiguous_json else None,
        mode=payload.get("mode", "guidance_enrichment"),
        max_guidance_terms=int(payload.get("max_guidance_terms", 20)),
        max_see_also_links=int(payload.get("max_see_also_links", 10)),
    )


def load_config(repo_root: Path | None = None) -> AppConfig:
    root = repo_root or Path.cwd()
    config_path = root / "config.yaml"
    local_config_path = root / "config.local.yaml"
    config_data = _read_yaml_if_exists(config_path)
    local_data = _read_yaml_if_exists(local_config_path)
    merged = {**config_data, **local_data}

    provider = {**(merged.get("provider") or {})}
    families = _family_map(provider)
    primary_payload = provider.get("primary") or {
        "backend": provider.get("backend", os.getenv("LIT_WIKI_PROVIDER", "heuristic")),
        "model": provider.get("model", os.getenv("LIT_WIKI_MODEL", "gemma-4-e4b-it")),
        "api_base": provider.get("api_base", os.getenv("LIT_WIKI_API_BASE", "")),
        "api_key_env": provider.get("api_key_env", os.getenv("LIT_WIKI_API_KEY_ENV", "LIT_WIKI_API_KEY")),
        "timeout_seconds": int(provider.get("timeout_seconds", os.getenv("LIT_WIKI_TIMEOUT_SECONDS", "60"))),
    }

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

    retry_payload = provider.get("retry_policy") or {}
    approval_payload = provider.get("approval") or {}
    budget_payload = provider.get("budget") or {}

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
        budget_ledger_file=cache_dir / "budget_ledger.json",
        local_config_file=local_config_path,
        env_file=root / ".env",
        primary_provider=_provider_spec_from_mapping("primary", primary_payload, families),
        model_families=families,
        fallback_providers=_fallback_specs(provider.get("fallbacks"), families),
        retry_policy=RetryPolicyConfig(
            local_max_attempts=int(retry_payload.get("local_max_attempts", 2)),
        ),
        approval_policy=ApprovalPolicyConfig(
            required=bool(approval_payload.get("required", True)),
            default_decision=str(approval_payload.get("default_decision", "prompt")),
        ),
        budget_policy=BudgetPolicyConfig(
            max_input_chars_per_request=int(budget_payload.get("max_input_chars_per_request", 12000)),
            max_output_tokens_per_request=int(budget_payload.get("max_output_tokens_per_request", 1200)),
            max_requests_per_file=int(budget_payload.get("max_requests_per_file", 4)),
            max_tokens_per_file=int(budget_payload.get("max_tokens_per_file", 12000)),
            max_tokens_per_day=int(budget_payload.get("max_tokens_per_day", 50000)),
            max_estimated_cost_per_file=float(budget_payload.get("max_estimated_cost_per_file", 0.0)),
            max_estimated_cost_per_day=float(budget_payload.get("max_estimated_cost_per_day", 0.0)),
        ),
        keyword_policy=_keyword_policy(root, merged),
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
