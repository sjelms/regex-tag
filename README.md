# Regex Tag + Literature Wiki

This repo now supports two related workflows:

1. Legacy bibliography and keyword-linking utilities for an Obsidian vault.
2. A bibliography-first literature wiki pipeline that ingests scholarly sources and writes managed source notes to `wiki/sources/`.

The literature wiki path is strict by design:

- Raw inputs go into `watch/`
- Generated source notes go into `wiki/sources/`
- Bibliography identity always stays the citekey
- Generated notes use `<citekey>_wiki.md`
- `key` in note YAML always points to the bibliography note as `"[[@<citekey>]]"`

Raw files should never be stored under `wiki/`. The lint command will flag them.

## Literature Wiki Workflow

### Directory model

```text
watch/              raw input queue
watch/processed/    archived successful inputs
watch/other/        failed or review-blocked inputs
extracted/          cleaned extracted text used for analysis
wiki/sources/       generated source notes only
wiki/index.md       managed source index
wiki/log.md         ingest log
wiki/overview.md    rolling overview
```

### Supported source matching

- Markdown with YAML `citation-key`
- EPUB or EPUB package with `iTunesMetadata.plist`
- PDF filename using `[Title]_[Authors]_[year].pdf`

### Ingest path

```bash
python main.py bib sync
python main.py watch run
```

The queue is sequential. One file is processed at a time. A successful input is archived to `watch/processed/`; failures and review-blocked items go to `watch/other/`.

### Output contract

- Generated source notes: `wiki/sources/<citekey>_wiki.md`
- Internal bibliography link: `key: "[[@<citekey>]]"`
- Entry type link: `type: "[[@<entry_type>]]"`
- Complete `author - N` and `editor - N` YAML emission from BibTeX
- `Related References` links to bibliography notes as `[[@citekey]]`, not assumed `_wiki` pages

## Keyword policy

The controlled vocabulary is guidance-first, not blind rewrite.

- Ambiguous aliases are not auto-emitted into note YAML
- Metadata enrichment is capped and conservative
- BibTeX keywords are preserved and deduped
- Source-note `tag` and `see also` should stay small and topic-relevant

## Extraction policy

- PDFs use `pypdf` extraction first
- EPUBs use `ebooklib` + `beautifulsoup4`
- Extracted text is cleaned before analysis:
  - control characters removed
  - broken Unicode normalized
  - common line-wrap artifacts repaired
  - publisher/download boilerplate stripped where possible

## Lint

```bash
python main.py lint
```

The lint report checks for:

- broken wiki links
- broken bibliography links
- raw source files stored under `wiki/`
- future-dated bibliography references
- suspiciously large metadata blocks
- extraction artifacts in cleaned extracted text

## Legacy utilities

The original bibliography-linking workflow still exists in this repo for vault maintenance:

- generate authors
- generate keyword catalogues
- link authors in notes
- link keywords in notes
- optionally disambiguate ambiguous keyword aliases with an LLM

Those utilities remain separate from the literature wiki ingest path. The literature wiki pipeline does not blindly rewrite source-note prose with keyword wikilinks.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For local LLM use, keep live provider settings in `config.local.yaml` or `.env`.

## Main commands

```bash
python main.py bib sync
python main.py source register --file path/to/source.md
python main.py extract --citekey Example2024-ab
python main.py ingest --citekey Example2024-ab
python main.py watch run
python main.py lint
python main.py graph build
```
