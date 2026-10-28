# Kristalizer 1.2 — migrated KQ scan correction

## Why this update?

In some Kristals created through bulk migrations, KQs represent **metadata values** (`dik:metadata-value:`), **numbered assertion referents** (`:concept:...:01`), or **source records** (`urn:foodkristal:source:`). None should be automatically matched to a Wikidata concept based on its label.

Kristalizer 1.1 generated 515 suggestions for the four Demography, FoodBrands, Media, and Telecommunications Kristals. **All 515 came from categorical metadata values**, not knowledge subjects.

## Version 1.2 scan

- Reads `identity-migration-map.json` to identify these roles.
- Removes irrelevant matches from the active registry, **without deleting their decisions**: they can be recovered from `ANALYSE/DECISIONS_ARCHIVEES.csv`.
- `ANALYSE/CANDIDATS_EXCLUS.csv` documents removed pairs.
- Scans `knowledge-base/sources/*.json` files of type `*.claim-set.*`, identifies topics, the number of claims, and a sample assertion.
- `ANALYSE/NOTIONS_DOMAINE.csv` lists the **documentary concepts to model**; `existing_kq` is intentionally blank.
- If EncyK is connected, `ANALYSE/SUGGESTIONS_NOTIONS_WIKIDATA.csv` offers QID suggestions **without assigning them a KQ**.

## How to use

1. Make a backup of `SORTIE` before updating (as a precaution).
2. Install the 1.2 repository archive into a **new Kristalizer directory** (or replace only the program files).
3. Keep the paths to the four projects, EncyK, and SORTIE in the GUI.
4. Run **1. Analyser** (“Analyze”). Then inspect `RAPPORT.json`, `NOTIONS_DOMAINE.csv`, and `SUGGESTIONS_NOTIONS_WIKIDATA.csv`.
5. **Do not start approval staging** until the concepts have been modeled as genuine KQs and supported by evidence.

FoodBrands contains a **source catalog**, not a database of brands/products: the claim sets contain no brand subjects to extract. This tool does not invent missing data.

## Compliance

- No changes to source directories or the EncyK index.
- No invented KQ/KA/KS identities and no automatic publication.
- Existing `.csv` files and decisions are retained or archived, including across repeated scans.
