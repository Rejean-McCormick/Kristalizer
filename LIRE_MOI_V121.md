# Kristalizer 1.2.1 — console Unicode fix

## Fix

In the Tkinter log, Windows could display `requi�rent` or `utilis�`: the child process emitted text in the Windows code page while the GUI decoded it as UTF-8. The launcher now sets `PYTHONIOENCODING=utf-8:replace`, `PYTHONUTF8=1`, and `KRISTALIZER_UTF8=1`; the GUI forces the same configuration for subprocesses. Both `.cmd` files select code page 65001.

The engine preserves Unicode characters in JSON reports and UTF-8-BOM CSV files. KQ, KS, and KA approval rules have not changed.

## Wikidata concept suggestions

Suggestions with matching names but descriptions clearly referring to a creative work, album, film, scientific article, song, patent, or namesake are flagged as `HORS_DOMAINE_PROBABLE` or `HOMONYMIE`. They remain in full in `SUGGESTIONS_NOTIONS_WIKIDATA.csv` for auditing; nothing is automatically deleted or rejected. This is a heuristic filter.

## Installation

Extract the ZIP into a new `Kristalizer` directory or replace the existing program files **without overwriting `SORTIE`**. Then run `LANCER_KRISTALIZER.cmd` and select “1. Analyser” (Analyze). The analysis does not modify any source Kristal.

## Quick verification

The log must display accents correctly in `requièrent`, `utilisé`, `décisions archivées`, and `FIN : succès` without replacement characters (`�`).

Tests: `py -3 -m unittest discover -s tests -v`. This version was tested on Linux with a simulated Windows code page; graphical rendering still needs confirmation on your Windows machine.
