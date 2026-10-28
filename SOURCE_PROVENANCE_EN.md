# Sources and scope

This refactoring starts from `Kristalizer_EN_reupload_2026-10-28.zip` (translated
Kristalizer 1.2.2) and compares its embedded Kit with the independently supplied
`znapshot_Kristal-Authoring-Kit_10281000.zip` (Kit 4.0.0-draft.4). No Kit files
are embedded or modified in this distribution. No remote GitHub repository was
changed.

Kristalizer's existing application implementation is preserved except for the
external-Kit integration boundary (CLI, GUI, resolver and build provenance), plus
new tests and documentation. The rest of the code can still contain French GUI
labels and runtime messages because this is an architectural update, not a GUI
localization release.
