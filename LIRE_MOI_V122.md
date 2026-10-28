# Version 1.2.2

New scan features:

- `LIAISONS_NOTIONS_ASSERTIONS.csv`: exact linkage between claims from knowledge sources and existing project KQ/KA identities through the v11 migration map. The software does not invent identities.
- `REVUE_IDENTITES_NOTIONS.csv`: a concept-by-concept review and Wikidata candidates excluding obvious out-of-domain namesakes or publications.
- Expanded description filter for `scientific article`, `journal article`, `book by`, and `US patent`.

Analysis is strictly non-destructive; it does not automatically create KQ, KS, KA, or `exactMatch` records.

Previous results remain readable. Open `LANCER_KRISTALIZER.cmd` and click “1. Analyser” (Analyze) for future Kristals.
