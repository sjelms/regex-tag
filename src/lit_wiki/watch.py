from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .config import AppConfig
from .models import ApprovalRequest, ProviderUsage, WatchSummary


SUPPORTED_FILE_SUFFIXES = {".pdf", ".epub", ".md", ".markdown", ".xhtml", ".html", ".htm"}


def iter_watch_items(config: AppConfig) -> list[Path]:
    items: list[Path] = []
    for path in sorted(config.watch_dir.iterdir()):
        if path.name.startswith("."):
            continue
        if path == config.processed_dir or path == config.other_dir:
            continue
        if path.is_dir():
            if (path / "iTunesMetadata.plist").exists():
                items.append(path)
            continue
        if path.suffix.lower() in SUPPORTED_FILE_SUFFIXES:
            items.append(path)
    return items


def archive_watch_item(item: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / item.name
    if not target.exists():
        return Path(shutil.move(str(item), str(target)))

    index = 1
    while True:
        candidate = destination_dir / f"{item.stem}_{index}{item.suffix}"
        if item.is_dir():
            candidate = destination_dir / f"{item.name}_{index}"
        if not candidate.exists():
            return Path(shutil.move(str(item), str(candidate)))
        index += 1


def show_final_dialog(summary: WatchSummary) -> None:
    if shutil.which("osascript") is None:
        return

    time_min = int(summary.elapsed_seconds // 60)
    time_sec = int(summary.elapsed_seconds % 60)
    time_str = f"{time_min}m {time_sec}s" if time_min else f"{time_sec}s"
    applescript = f"""
    display dialog "Literature Wiki Batch Summary

    ✅ Files processed successfully: {summary.success_count}
    ⚠️ Files with issues: {summary.issue_count}
    ❌ Files failed: {summary.fail_count}

    📄 PDFs: {summary.pdf_count}
    📚 EPUBs: {summary.epub_count}
    📝 Text/Markdown: {summary.markdown_count}
    📦 Other: {summary.other_count}

    🕒 Time elapsed: {time_str}
    " buttons {{"OK"}} default button "OK" with title "Literature Wiki"
    """
    subprocess.run(["osascript", "-e", applescript], check=False)


def _show_dialog(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    return (result.stdout or "").strip()


def resolve_fallback_approval(config: AppConfig, request: ApprovalRequest) -> str:
    default_decision = config.approval_policy.default_decision.lower()
    if default_decision in {"approve", "skip", "cancel"}:
        return default_decision
    if shutil.which("osascript") is None:
        return "skip"

    applescript = f"""
    set theButton to button returned of (display dialog "Fallback approval required

    Source: {request.source_name}
    Citekey: {request.citekey}
    Reason: {request.reason}

    Primary model: {request.primary_model}
    Fallback provider: {request.fallback_provider}
    Fallback model: {request.fallback_model}

    Estimated requests: {request.estimated_chunk_count}
    Estimated total tokens: {request.usage.estimated_total_tokens}
    Daily tokens: {request.current_daily_tokens} / {request.max_daily_tokens}
    " buttons {{"Cancel Queue", "Skip to Review", "Approve"}} default button "Approve" with title "Literature Wiki")
    return theButton
    """
    result = _show_dialog(applescript)
    mapping = {
        "Approve": "approve",
        "Skip to Review": "skip",
        "Cancel Queue": "cancel",
    }
    return mapping.get(result, "skip")


def show_fallback_complete_dialog(citekey: str, title: str, usage: ProviderUsage) -> None:
    if shutil.which("osascript") is None:
        return
    applescript = f"""
    display dialog "Fallback processing complete

    Source: {title}
    Citekey: {citekey}
    Fallback provider: {usage.provider_name}
    Model: {usage.model}
    Requests: {usage.requests_made}
    Estimated tokens: {usage.estimated_total_tokens}

    Control has returned to local processing.
    " buttons {{"OK"}} default button "OK" with title "Literature Wiki"
    """
    subprocess.run(["osascript", "-e", applescript], check=False)


def show_info_dialog(message: str) -> None:
    if shutil.which("osascript") is None:
        return
    escaped = message.replace('"', '\\"')
    applescript = f"""
    display dialog "{escaped}" buttons {{"OK"}} default button "OK" with title "Literature Wiki"
    """
    subprocess.run(["osascript", "-e", applescript], check=False, capture_output=True, text=True)


def timed_watch_run(fn):
    start = time.monotonic()
    summary = fn()
    summary.elapsed_seconds = time.monotonic() - start
    return summary
