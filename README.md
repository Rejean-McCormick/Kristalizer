> **Version 1.2.2 update:** fixed accented characters in the Windows log and added warnings for obvious namesakes in Wikidata suggestions. See [`LIRE_MOI_V121.md`](LIRE_MOI_V121.md).

> **New in 1.2:** the scan now distinguishes migrated metadata, assertion referents, and domain concepts. Read `LIRE_MOI_V12.md` before approving Wikidata mappings.

# Kristalizer

**Kristal analysis, Wikidata identity reconciliation, and canonical build workflow.**

Kristalizer helps prepare and evolve **one Kristal or any number of Kristals**, using EncyKlopedia/Wikidata as an external reference and one independently installed canonical Kristal Authoring Kit for local builds and activation. It replaces the old *Bridge Kristal Universel* interface.

## Getting started on Windows

1. Extract the repository ZIP into a directory, for example `C:\mycode\Kristal\Kristalizer`.
2. Keep the official **Kristal-Authoring-Kit** directory separately, ideally alongside **Kristalizer** (never inside `vendor/`). Do not copy its sources into Kristalizer.
3. Double-click **`LANCER_KRISTALIZER.cmd`**. Python 3.10+ with Tkinter is required; no `pip install` is needed for the standalone archive.
4. Select a **single Kristal** directory (containing `kristal.workspace.json`) or a parent directory containing multiple projects.
5. Confirm the path to `D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite`, if available. The engine also works without the index, with more limited coverage.
6. Click **1. Analyser** (“Analyze”), then proceed in order.

The default output location is `Kristalizer\SORTIE`. You can change this path. **Do not choose the source directory as the output directory.**

## The four-step workflow

| Step | Action | Modifies the sources? |
| --- | --- | --- |
| 1. **Analyze** | Finds KQ/KP identities, reads crosswalks and available Skope data, queries the EncyK index read-only, and writes `ANALYSE/CANDIDATS.csv`, `DECISIONS.csv`, and `RAPPORT.json`. | No |
| 2. **Prepare copies** | Clones workspaces under `SORTIE/STAGING/` and generates crosswalks based on **approved decisions** backed by an existing KS. | No |
| 3. **Validate and build** | Runs Kit commands `check-v11`, `check`, and `build-v9`, **only on the copies**. | No |
| 4. **Publish and activate** | Also runs `publish-v9` and `activate-v9 --channel current`, **only on the copies**. | No |

Activation is **local**. It does not send anything to GitHub, write to EncyK, or modify the original Kristal.

## KQ–QID and KP–PID decisions

In `SORTIE/ANALYSE/DECISIONS.csv`, each row has a state: `pending`, `rejected`, or `approved`.
Approval requires `reviewer`, `reason`, and `evidence_refs` pointing to KS records present in the project's graph. An existing KS **does not automatically constitute sufficient Wikidata evidence**: review its meaning and provenance before approving any match.

To recover decisions from historical versions v1–v13, select **Importer anciennes décisions** (Import previous decisions) and choose their CSV file. Unrecognized rows are saved and reported; they are not silently approved. Legacy staging files (`BRIDGE_STAGE_REPORT.json` and `BRIDGE_PENDING_ACTIVATION.json`) remain readable.

## Future Kristals: operation and limitations

- You may use any number of Kristals with any names; no group of 56 or other fixed batch is required.
- Without Skope files, Kristalizer can search names and aliases in the local EncyK index.
- A project without complete v11 artifacts is marked **v11 migration required**: KQ/KP identities and assertions are never invented.
- The tool **does not yet bulk-convert** Wikidata statements into **domain-level** KA/KS assertions. Detailed evidence, conversion, and semantic verification of these new facts belong to the next **v11.1 enrichment** phase.
- Lexical matches and scores are never sufficient to create a canonical `exactMatch`.
- **No Authoring Kit is bundled.** The minimum independently installed Kit accepted by Kristalizer is `4.0.0-draft.4` (Framework v11 pin `11.0.0-draft.4`), as supplied separately. Future Kit 4.x versions are checked for interface compatibility before builds; a future Framework pin that does not match the expected v11 family is rejected until reviewed. Compatibility is **not** a claim of complete release qualification.

## One canonical Authoring Kit (no duplicates)

Use the following layout, or choose the same external Kit path in the GUI:

```text
mycode/
  Kristal-Authoring-Kit/        # ONE authoritative, independently updated checkout
    VERSION
    tools/kristal.py
  Kristalizer/                  # no vendor/ or Kit copy
    kristalizer.py
    Kristalizer.pyw
```

Find and validate the Kit before building: `py -3 kristalizer.py kit-status`. You can select it in the GUI's **External Authoring Kit** field, pass `--kit "C:\mycode\Kristal-Authoring-Kit"` on `build`/`kit-status`, or set `KRISTAL_AUTHORING_KIT_HOME`. Resolution priority is command-line selection, environment, saved GUI configuration, then the sibling directory. A missing, outdated, or ambiguous Kit **stops the build**; Kristalizer never silently downloads or uses an embedded copy. `scan` and `stage` work without the Kit.

**Note:** the Kit is the authority for workspace authoring/building. Kristalizer is an analysis/orchestration layer. See [EXTERNAL_AUTHORING_KIT.md](EXTERNAL_AUTHORING_KIT.md) for version checks and migration from the old vendored layout.

## Command-line usage

```bat
py -3 kristalizer.py scan --source "C:\mes-kristals" --output "C:\KristalizerSortie" --index "D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite"
py -3 kristalizer.py import-decisions --file "C:\ancien-bridge\02_DECISIONS.csv" --output "C:\KristalizerSortie"
py -3 kristalizer.py stage --source "C:\mes-kristals" --output "C:\KristalizerSortie"
py -3 kristalizer.py build --staging "C:\KristalizerSortie\STAGING\<id>"
py -3 kristalizer.py build --staging "C:\KristalizerSortie\STAGING\<id>" --publish --activate
py -3 kristalizer.py status --output "C:\KristalizerSortie"
```

Tests: `py -3 -m unittest discover -s tests -v`. GUI: `Kristalizer.pyw`. English GitHub description: [`GITHUB_DESCRIPTION.txt`](GITHUB_DESCRIPTION.txt).

## Repository layout

`kristalizer/`: engine and CLI; `Kristalizer.pyw`: Tkinter GUI; `kristalizer/kit_reference.py`: external dependency resolver; `tests/`: regression tests; `NOTES_TECHNIQUES.md`: architecture.

This repository contains no keys, local configuration, large extraction results, or Wikidata dumps. The local `kristalizer-config.json` configuration is ignored by Git.
