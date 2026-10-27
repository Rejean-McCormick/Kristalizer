## 1.2.1

- Force UTF-8 in the GUI subprocess and Windows launchers, fixing mojibake in French console output.
- Retains all Wikidata topic suggestions but flags clearly unrelated named works for review.
- Adds regression tests for Windows ANSI pipe encoding and topic homonyms.

## 1.2.0 — Scan sensible aux rôles d'identité

- Détecte les KQ métadonnées, référents d'assertion et fiches documentaires migrées.
- Évite les faux `exactMatch` obtenus par simple égalité de libellé.
- Extrait les sujets des `claim-set` comme **notions à modéliser**, sans inventer des KQ.
- Archive les anciennes décisions et exclusions lors des scans successifs.
- Préserve la chaîne staging / build / activation du logiciel 1.1.

# Changelog

## 1.2.0 — Kristalizer (renommage du dépôt et du produit)

- Nom, GUI, lanceurs, CLI, paquet Python, métadonnées et documentation regroupés sous **Kristalizer**.
- Nouvelles sorties `KRISTALIZER_STAGE_REPORT.json` et `KRISTALIZER_BUILD_REPORT.json`, sans perdre la lecture des anciens rapports Bridge.
- Import des anciens états de décisions et migration de l'ancienne configuration d'interface.
- ZIP autonome avec le Kit fourni ; exemples pour un projet seul ou n'importe quel dossier de Kristals.
- Ne change pas le périmètre d'enrichissement des KA/KS : celui-ci viendra dans le travail v11.1.

## 1.0.0 — Base universelle antérieure

- Quatre actions de scan, staging, construction et activation en remplacement des outils spécialisés v1–v13.
- Requêtes EncyK en lecture seule, candidats Skope facultatifs et conservation des décisions.
