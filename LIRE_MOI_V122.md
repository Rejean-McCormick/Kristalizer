# Version 1.2.2

Nouveautés du scan :

- `LIAISONS_NOTIONS_ASSERTIONS.csv` : lien exact entre les `claims` des sources de connaissance et les KQ/KA existants du projet, via la carte de migration v11. Le logiciel n’invente pas d’identités.
- `REVUE_IDENTITES_NOTIONS.csv` : bilan par notion et candidats Wikidata ne correspondant pas à une homonymie ou publication manifestement hors domaine.
- Filtre de descriptions étoffé pour `scientific article`, `journal article`, `book by` et `US patent`.

Analyse strictement non destructive; aucune création automatique de KQ, KS, KA ou d’`exactMatch`.

Les anciens résultats restent lisibles. Ouvre `LANCER_KRISTALIZER.cmd` et clique sur « 1. Analyser » pour les futurs Kristals.
