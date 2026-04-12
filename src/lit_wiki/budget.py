from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .config import BudgetPolicyConfig
from .models import ProviderUsage


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def estimated_chunk_count(text: str, max_input_chars_per_request: int) -> int:
    if not text:
        return 1
    if max_input_chars_per_request <= 0:
        return 1
    return max(1, (len(text) + max_input_chars_per_request - 1) // max_input_chars_per_request)


def estimate_usage(
    provider_name: str,
    model: str,
    text: str,
    budget: BudgetPolicyConfig,
) -> ProviderUsage:
    chunk_count = estimated_chunk_count(text, budget.max_input_chars_per_request)
    requests_made = min(chunk_count, max(1, budget.max_requests_per_file))
    input_tokens = sum(
        estimate_tokens(text[index:index + budget.max_input_chars_per_request])
        for index in range(0, min(len(text), requests_made * budget.max_input_chars_per_request), budget.max_input_chars_per_request)
    )
    output_tokens = requests_made * budget.max_output_tokens_per_request
    return ProviderUsage(
        provider_name=provider_name,
        model=model,
        requests_made=requests_made,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_total_tokens=input_tokens + output_tokens,
        estimated_cost=0.0,
    )


def load_budget_ledger(path: Path) -> dict:
    if not path.exists():
        return {"date": date.today().isoformat(), "entries": [], "total_tokens": 0, "total_cost": 0.0}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("date") != date.today().isoformat():
        return {"date": date.today().isoformat(), "entries": [], "total_tokens": 0, "total_cost": 0.0}
    return payload


def save_budget_ledger(path: Path, ledger: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(ledger, handle, indent=2, ensure_ascii=False)


def can_spend(ledger: dict, usage: ProviderUsage, budget: BudgetPolicyConfig) -> tuple[bool, str]:
    if usage.estimated_total_tokens > budget.max_tokens_per_file:
        return False, "per-file token cap exceeded"
    if budget.max_estimated_cost_per_file > 0 and usage.estimated_cost > budget.max_estimated_cost_per_file:
        return False, "per-file cost cap exceeded"
    if ledger.get("total_tokens", 0) + usage.estimated_total_tokens > budget.max_tokens_per_day:
        return False, "daily token cap exceeded"
    if budget.max_estimated_cost_per_day > 0 and ledger.get("total_cost", 0.0) + usage.estimated_cost > budget.max_estimated_cost_per_day:
        return False, "daily cost cap exceeded"
    return True, ""


def record_spend(path: Path, usage: ProviderUsage, citekey: str) -> dict:
    ledger = load_budget_ledger(path)
    ledger["entries"].append({"citekey": citekey, **asdict(usage)})
    ledger["total_tokens"] = ledger.get("total_tokens", 0) + usage.estimated_total_tokens
    ledger["total_cost"] = ledger.get("total_cost", 0.0) + usage.estimated_cost
    save_budget_ledger(path, ledger)
    return ledger
