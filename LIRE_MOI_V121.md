# Kristalizer 1.2.1 — correction Unicode de la console

## Correction

Dans le journal Tkinter, Windows pouvait afficher `requi�rent` ou `utilis�` : le processus enfant émettait du texte dans la page de codes Windows, alors que le GUI le décodait en UTF-8. Le lanceur définit désormais `PYTHONIOENCODING=utf-8:replace`, `PYTHONUTF8=1` et `KRISTALIZER_UTF8=1`; le GUI force la même configuration pour les sous-processus. Les deux `.cmd` sélectionnent la page de codes 65001.

Le moteur conserve les caractères Unicode dans les rapports JSON et CSV UTF-8-BOM. Aucun changement n'est apporté aux règles d'approbation des KQ, KS ou KA.

## Suggestions de notions Wikidata

Les propositions qui correspondent par le nom mais dont la description désigne clairement une œuvre, un album, un film, un article scientifique, une chanson, un brevet ou une homonymie sont signalées comme `HORS_DOMAINE_PROBABLE` ou `HOMONYMIE`. Elles restent intégralement dans `SUGGESTIONS_NOTIONS_WIKIDATA.csv` pour audit; rien n'est effacé ou rejeté automatiquement. Ce filtre est heuristique.

## Installation

Extraire le ZIP dans un nouveau dossier `Kristalizer` ou remplacer les fichiers du programme existants **sans écraser `SORTIE`**, puis lancer `LANCER_KRISTALIZER.cmd` et l'action « 1. Analyser ». L'analyse ne modifie aucun Kristal source.

## Vérification rapide

Le journal doit afficher les accents de `requièrent`, `utilisé`, `décisions archivées` et `FIN : succès` sans caractères de remplacement `�`.

Tests: `py -3 -m unittest discover -s tests -v`. Cette version est testée sous Linux avec une page de codes Windows simulée; son rendu graphique reste à confirmer sur ton Windows.
