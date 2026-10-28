> **Version 1.2.2 update:** fixed accented characters in the Windows log and added warnings for obvious namesakes in Wikidata suggestions. See [`LIRE_MOI_V121.md`](LIRE_MOI_V121.md).

> **New in 1.2:** the scan now distinguishes migrated metadata, assertion referents, and domain concepts. Read `LIRE_MOI_V12.md` before approving Wikidata mappings.

# Kristalizer

**Kristal analysis, Wikidata identity reconciliation, and canonical build workflow.**

Kristalizer helps prepare and evolve **one Kristal or any number of Kristals**, using EncyKlopedia/Wikidata as an external reference and the bundled Kristal Authoring Kit for local builds and activation. It replaces the old *Bridge Kristal Universel* interface.

## Getting started on Windows

1. Extract the repository ZIP into a directory, for example `C:\mycode\Kristal\Kristalizer`.
2. Double-click **`LANCER_KRISTALIZER.cmd`**. Python 3.10+ with Tkinter is required; no `pip install` is needed for the standalone archive.
3. Select a **single Kristal** directory (containing `kristal.workspace.json`) or a parent directory containing multiple projects.
4. Confirm the path to `D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite`, if available. The engine also works without the index, with more limited coverage.
5. Click **1. Analyser** (“Analyze”), then proceed in order.

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
- The bundled Kit contracts are pinned to Framework `11.0.0-draft.3`. Official qualification against `draft.4` requires separate version alignment.

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

`kristalizer/`: engine and CLI; `Kristalizer.pyw`: Tkinter GUI; `vendor/Kristal-Authoring-Kit/`: unchanged bundled dependency; `tests/`: regression tests; `NOTES_TECHNIQUES.md`: architecture.

This repository contains no keys, local configuration, large extraction results, or Wikidata dumps. The local `kristalizer-config.json` configuration is ignored by Git.
