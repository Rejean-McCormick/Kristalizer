> **Mise à jour 1.2.1 :** correction des accents dans le journal Windows et signalement des homonymies évidentes dans les suggestions Wikidata. Voir [`LIRE_MOI_V121.md`](LIRE_MOI_V121.md).

> **Nouveau en 1.2 :** le scan distingue métadonnées migrées, référents d'assertion et notions de domaine. Consulter `LIRE_MOI_V12.md` avant d'approuver des correspondances Wikidata.

# Kristalizer

**Kristal analysis, Wikidata identity reconciliation, and canonical build workflow.**

Kristalizer helps prepare and evolve **one Kristal or any number of Kristals**, using EncyKlopedia/Wikidata as an external reference and the bundled Kristal Authoring Kit for local builds and activation. It replaces the old *Bridge Kristal Universel* interface.

## Démarrer sur Windows

1. Extraire le ZIP du dépôt dans un dossier, par exemple `C:\mycode\Kristal\Kristalizer`.
2. Double-cliquer sur **`LANCER_KRISTALIZER.cmd`**. Python 3.10+ avec Tkinter est requis ; aucun `pip install` n'est nécessaire pour l'archive autonome.
3. Choisir un dossier de **Kristal unique** (contenant `kristal.workspace.json`) ou un dossier parent contenant plusieurs projets.
4. Confirmer le chemin vers `D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite`, si disponible. Le moteur fonctionne aussi sans index, avec une couverture plus limitée.
5. Cliquer sur **1. Analyser**, puis procéder dans l'ordre.

La sortie par défaut est `Kristalizer\SORTIE`. Le chemin peut être changé. **Ne pas choisir la source comme dossier de sortie.**

## Le parcours en quatre étapes

| Étape | Effet | Modifie les sources ? |
| --- | --- | --- |
| 1. **Analyser** | Découvre les KQ/KP, lit les crosswalks et les données Skope disponibles, interroge l'index EncyK en lecture seule et écrit `ANALYSE/CANDIDATS.csv`, `DECISIONS.csv`, `RAPPORT.json`. | Non |
| 2. **Préparer les copies** | Clone les workspaces sous `SORTIE/STAGING/` et produit les crosswalks issus de **décisions approuvées** et assorties d'une KS existante. | Non |
| 3. **Vérifier et construire** | Sur les copies uniquement, utilise le Kit pour `check-v11`, `check`, `build-v9`. | Non |
| 4. **Publier et activer** | Sur les copies uniquement, exécute aussi `publish-v9`, `activate-v9 --channel current`. | Non |

L'activation est **locale**. Elle n'envoie rien sur GitHub, n'écrit pas dans EncyK et ne modifie pas le Kristal d'origine.

## Décisions KQ–QID et KP–PID

Dans `SORTIE/ANALYSE/DECISIONS.csv`, chaque ligne porte un état : `pending`, `rejected` ou `approved`.
Une approbation exige `reviewer`, `reason` et `evidence_refs` pointant vers des KS présentes dans le graphe du projet. Une KS existante **n'est pas automatiquement une preuve Wikidata suffisante** : vérifier son sens et sa provenance avant toute approbation.

Pour reprendre les arbitrages des versions historiques v1–v13, utiliser **Importer anciennes décisions** et sélectionner leur CSV. Les lignes non reconnues sont sauvegardées et signalées, sans être approuvées silencieusement. Les anciens fichiers de staging (`BRIDGE_STAGE_REPORT.json` et `BRIDGE_PENDING_ACTIVATION.json`) restent lisibles.

## Futurs Kristals : fonctionnement et limites

- Le nombre et les noms de Kristals sont libres ; aucun groupe de 56 ni lot fixe n'est nécessaire.
- Sans fichiers Skope, Kristalizer peut rechercher les noms et alias dans l'index local EncyK.
- Un projet sans artefacts v11 complets est marqué **migration v11 requise** : les identités KQ/KP et les assertions ne sont pas inventées.
- L'outil **ne convertit pas encore en masse** les statements Wikidata en assertions KA/KS **de domaine**. Les preuves détaillées, la conversion et la vérification sémantique de ces nouveaux faits relèvent de la phase suivante d'enrichissement **v11.1**.
- Les correspondances lexicales et les scores ne suffisent jamais à créer un `exactMatch` canonique.
- Les contrats du Kit inclus sont épinglés sur Framework `11.0.0-draft.3`. Une qualification officielle avec `draft.4` requiert un alignement de versions indépendant.

## Commandes sans interface

```bat
py -3 kristalizer.py scan --source "C:\mes-kristals" --output "C:\KristalizerSortie" --index "D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite"
py -3 kristalizer.py import-decisions --file "C:\ancien-bridge\02_DECISIONS.csv" --output "C:\KristalizerSortie"
py -3 kristalizer.py stage --source "C:\mes-kristals" --output "C:\KristalizerSortie"
py -3 kristalizer.py build --staging "C:\KristalizerSortie\STAGING\<id>"
py -3 kristalizer.py build --staging "C:\KristalizerSortie\STAGING\<id>" --publish --activate
py -3 kristalizer.py status --output "C:\KristalizerSortie"
```

Tests : `py -3 -m unittest discover -s tests -v`. Interface : `Kristalizer.pyw`. Description anglaise pour GitHub : [`GITHUB_DESCRIPTION.txt`](GITHUB_DESCRIPTION.txt).

## Composition du dépôt

`kristalizer/` : moteur et CLI ; `Kristalizer.pyw` : GUI Tkinter ; `vendor/Kristal-Authoring-Kit/` : dépendance fournie sans altération ; `tests/` : régressions ; `NOTES_TECHNIQUES.md` : architecture.

Pas de clé, de configuration locale, de résultats d'extraction volumineux ou de dumps Wikidata dans ce dépôt. La configuration locale `kristalizer-config.json` est ignorée par Git.
