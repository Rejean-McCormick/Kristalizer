# Architecture — Kristalizer 1.1

- `Kristalizer.pyw` : interface Tkinter sans dépendance tierce ; les traitements tournent dans un processus séparé.
- `kristalizer.py` : CLI autonome ; `kristalizer/cli.py` : point d'entrée équivalent pour une installation de développement.
- `kristalizer/core.py` : découverte de workspaces, EncyIndex SQLite lecture seule, dictionnaires v11, import Skope, analyse, préservation des décisions, préparation non destructive des crosswalks, puis exécution du Kit.
- `vendor/Kristal-Authoring-Kit` : copie inchangée du Kit d'origine et de ses contrats. Son verrou Framework v11 est `draft.3`.
- `tests/` : tests hors ligne sans dump Wikidata réel, avec base SQLite factice.

**Contrats de sortie (nouveaux)** : `ANALYSE/{CANDIDATS,DECISIONS,RAPPORT}.csv/json`, `STAGING/<id>/KRISTALIZER_STAGE_REPORT.json`, `STAGING/<id>/KRISTALIZER_BUILD_REPORT.json`, `<Kristal>/KRISTALIZER_PENDING_ACTIVATION.json`.

**Compatibilité historique** : le moteur peut reprendre les fichiers `BRIDGE_STAGE_REPORT.json` et `BRIDGE_PENDING_ACTIVATION.json`, ainsi que les décisions CSV des versions précédentes. Il préserve les identifiants historiquement enregistrés par le Kit ; voir les tests de régression.

**Garanties** : EncyK est ouvert avec SQLite `mode=ro`, aucune modification du dossier source ; toute publication/activation est limitée aux copies sous `STAGING` ; les décisions candidates n'entraînent aucune promotion canonique implicite.

**Limites** : le moteur ne réalise pas encore la promotion massive de connaissances de domaine Wikidata vers des KA/KS canoniques, et ne crée pas les artefacts v11 manquants pour un Kristal encore non migré. Cela relève de la prochaine phase v11.1.
