from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .config import AppConfig
from .models import WatchSummary


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


def timed_watch_run(fn):
    start = time.monotonic()
    summary = fn()
    summary.elapsed_seconds = time.monotonic() - start
    return summary
