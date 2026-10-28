# External Authoring Kit boundary — 2026-10-28

- Removed all 271 vendored Authoring Kit files from this Kristalizer distribution.
- The separately supplied canonical Kit snapshot is `4.0.0-draft.4`, compared with `4.0.0-draft.3` previously embedded.
- Builds now resolve a single external Kit, validate the v11 interface and report the exact selected version.
- Analysis and staging remain decoupled from the Kit; no source Kristal is modified.
- Existing GUI configuration can be reused after pointing its Kit field to the canonical installation.
- Previously generated translation/snapshot manifests describing the embedded Kit are excluded to avoid presenting stale inventories as authoritative.

No changes have been made to the upstream Authoring Kit archive or any GitHub repository.
