from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .service import (
    extract_source,
    ingest_batch,
    ingest_source,
    process_watch_folder,
    register_source,
    run_graph_build,
    run_lint,
    sync_bibliography,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bibliography-linked literature wiki engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bib_parser = subparsers.add_parser("bib", help="Bibliography operations")
    bib_subparsers = bib_parser.add_subparsers(dest="bib_command", required=True)
    bib_subparsers.add_parser("sync", help="Parse regex-tag.bib and refresh the local bibliography registry")

    source_parser = subparsers.add_parser("source", help="Source registration operations")
    source_subparsers = source_parser.add_subparsers(dest="source_command", required=True)
    register_parser = source_subparsers.add_parser("register", help="Register a source file against a bibliography entry")
    register_parser.add_argument("--file", required=True, help="Path to the source artifact")
    register_parser.add_argument("--citekey", help="Optional explicit citekey override")

    extract_parser = subparsers.add_parser("extract", help="Extract a registered source to canonical markdown")
    extract_parser.add_argument("--citekey", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Generate wiki source notes")
    ingest_parser.add_argument("--citekey")
    ingest_parser.add_argument("--batch", action="store_true")

    graph_parser = subparsers.add_parser("graph", help="Graph operations")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)
    graph_subparsers.add_parser("build", help="Build graph.json and graph.html from wiki links")

    watch_parser = subparsers.add_parser("watch", help="Process queued files from the watch folder")
    watch_subparsers = watch_parser.add_subparsers(dest="watch_command", required=True)
    watch_subparsers.add_parser("run", help="Process the current watch folder queue sequentially")

    subparsers.add_parser("lint", help="Generate a basic lint report for the wiki")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "bib" and args.bib_command == "sync":
        bibliography = sync_bibliography(config)
        print(f"Synced {len(bibliography.entries)} bibliography entries to {config.bibliography_registry_file}")
        return 0

    if args.command == "source" and args.source_command == "register":
        record, match = register_source(config, Path(args.file).expanduser(), citekey=args.citekey)
        print(
            f"Registered {record.source_path} -> {record.citekey} "
            f"(reason: {match.reason}, review: {record.needs_review})"
        )
        return 0

    if args.command == "extract":
        record = extract_source(config, args.citekey)
        print(f"Extracted {record.citekey} to {record.extracted_path}")
        return 0

    if args.command == "ingest":
        if args.batch:
            ingested = ingest_batch(config)
            print(f"Ingested {len(ingested)} source notes")
            return 0
        if not args.citekey:
            parser.error("ingest requires --citekey unless --batch is used")
        note_path = ingest_source(config, args.citekey)
        print(f"Wrote {note_path}")
        return 0

    if args.command == "graph" and args.graph_command == "build":
        nodes, edges = run_graph_build(config)
        print(f"Built graph with {nodes} nodes and {edges} edges")
        return 0

    if args.command == "watch" and args.watch_command == "run":
        summary = process_watch_folder(config)
        print(
            "Watch run complete: "
            f"success={summary.success_count} "
            f"issues={summary.issue_count} "
            f"failed={summary.fail_count} "
            f"pdf={summary.pdf_count} "
            f"epub={summary.epub_count} "
            f"markdown={summary.markdown_count} "
            f"other={summary.other_count} "
            f"elapsed={summary.elapsed_seconds:.2f}s"
        )
        return 0

    if args.command == "lint":
        report = run_lint(config)
        print(report.rstrip())
        return 0

    parser.error("Unhandled command")
    return 2
