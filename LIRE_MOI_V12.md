# Kristalizer 1.2 — correction du scan des KQ migrés

## Pourquoi cette mise à jour ?

Dans certains Kristals issus de migrations en masse, les KQ sont des **valeurs de métadonnées** (`dik:metadata-value:`), des **référents d'assertion numérotés** (`:concept:...:01`) ou des **fiches de source** (`urn:foodkristal:source:`). Aucun ne doit être automatiquement identifié à un concept Wikidata en fonction de son étiquette.

Kristalizer 1.1 a ainsi généré 515 propositions pour les quatre Kristals Demography, FoodBrands, Media et Telecommunications. **Toutes les 515 provenaient de valeurs catégorielles de métadonnées**, pas de sujets de connaissance.

## Scan v1.2

- Lit `identity-migration-map.json` pour identifier ces rôles.
- Retire les correspondances non pertinentes du registre actif, **sans effacer leurs décisions** : elles sont récupérables dans `ANALYSE/DECISIONS_ARCHIVEES.csv`.
- `ANALYSE/CANDIDATS_EXCLUS.csv` documente les paires retirées.
- Parcourt les `knowledge-base/sources/*.json` de type `*.claim-set.*`, repère les thèmes, leur nombre de claims et une assertion d'exemple.
- `ANALYSE/NOTIONS_DOMAINE.csv` fournit les **notions documentaires à modéliser**; `existing_kq` est volontairement vide.
- Si EncyK est connecté, `ANALYSE/SUGGESTIONS_NOTIONS_WIKIDATA.csv` fournit des suggestions de QID **sans leur attribuer de KQ**.

## Utilisation

1. Fais une copie du dossier `SORTIE` avant de mettre à jour (par prudence).
2. Installe l'archive du dépôt 1.2 dans un **nouveau dossier** Kristalizer (ou remplace les fichiers programme seulement).
3. Dans l'interface, conserve les chemins des quatre projets, d'EncyK et de SORTIE.
4. Lance **1. Analyser**. Examine ensuite `RAPPORT.json`, `NOTIONS_DOMAINE.csv` et `SUGGESTIONS_NOTIONS_WIKIDATA.csv`.
5. **Ne lance pas le staging d'approbations** tant que les notions n'ont pas été modélisées en véritables KQ et attestées.

FoodBrands contient un **catalogue de sources**, pas une base de marques/produits : aucun sujet de marques n'est présent à extraire via les claim-sets. Cet outil n'invente pas les données manquantes.

## Conformité

- Aucune modification du dossier source ni de l'index EncyK.
- Aucun KQ/KA/KS inventé et aucune publication automatique.
- Les anciens `.csv` et décisions sont conservés ou archivés, y compris après plusieurs scans.
