## 1.2.2

- Force UTF-8 in the GUI subprocess and Windows launchers, fixing mojibake in French console output.
- Retain all Wikidata topic suggestions but flag clearly unrelated named works for review.
- Add regression tests for Windows ANSI pipe encoding and topic homonyms.

## 1.2.0 — Identity-role-aware scanning

- Detect KQs representing metadata values, assertion referents, and migrated source records.
- Prevent false `exactMatch` mappings based solely on label equality.
- Extract subjects from `claim-set` records as **concepts to model**, without inventing KQs.
- Archive previous decisions and exclusions during successive scans.
- Preserve the staging/build/activation pipeline from software version 1.1.

# Changelog

## 1.2.0 — Kristalizer (repository and product renamed)

- Unify the name, GUI, launchers, CLI, Python package, metadata, and documentation under **Kristalizer**.
- Introduce `KRISTALIZER_STAGE_REPORT.json` and `KRISTALIZER_BUILD_REPORT.json` outputs while continuing to read legacy Bridge reports.
- Import previous decision states and migrate the former GUI configuration.
- Supply a standalone ZIP bundling the Kit, with examples for one project or any directory containing Kristals.
- Leave the scope of KA/KS enrichment unchanged; this work is planned for v11.1.

## 1.0.0 — Previous universal baseline

- Four scan, staging, build, and activation actions replace specialized v1–v13 tools.
- Read-only EncyK queries, optional Skope candidates, and decision preservation.
