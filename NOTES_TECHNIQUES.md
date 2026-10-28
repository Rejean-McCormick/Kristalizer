# Architecture — Kristalizer 1.1

- `Kristalizer.pyw`: Tkinter interface with no third-party dependency; processing runs in a separate process.
- `kristalizer.py`: standalone CLI; `kristalizer/cli.py`: equivalent entry point for development installations.
- `kristalizer/core.py`: workspace discovery, read-only SQLite EncyIndex, v11 dictionaries, Skope imports, analysis, decision preservation, non-destructive crosswalk preparation, then Kit execution.
- `kristalizer/kit_reference.py`: resolves the single external canonical Authoring Kit and checks version, Framework pin and required entrypoint commands before each build. No embedded Kit copy or automatic download.
- `tests/`: offline tests using a synthetic SQLite database, without a real Wikidata dump.

**New output contracts:** `ANALYSE/{CANDIDATS,DECISIONS,RAPPORT}.csv/json`, `STAGING/<id>/KRISTALIZER_STAGE_REPORT.json`, `STAGING/<id>/KRISTALIZER_BUILD_REPORT.json`, `<Kristal>/KRISTALIZER_PENDING_ACTIVATION.json`.

**Backward compatibility:** the engine can reuse `BRIDGE_STAGE_REPORT.json`, `BRIDGE_PENDING_ACTIVATION.json`, and CSV decisions from previous versions. It preserves identifiers historically recorded by the Kit; see regression tests.

**Guarantees:** A stale/missing Authoring Kit fails closed; the Kit is never duplicated or modified by Kristalizer. EncyK is opened with SQLite `mode=ro`; source directories are never modified. All publication/activation is limited to copies under `STAGING`; candidate decisions never imply canonical promotion.

**Limitations:** the engine does not yet bulk-promote Wikidata domain knowledge into canonical KA/KS records, and it does not create missing v11 artifacts for Kristals that have not been migrated. This is part of the next v11.1 phase.
