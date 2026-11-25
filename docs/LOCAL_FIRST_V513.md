# Local-first V5.13 — Kristalizer authority boundary

**Status:** candidate coordination note; owner instructions and exact pinned contracts prevail.

## Owned responsibilities

Kristalizer analyzes local Kristals and stages identity/Wikidata mapping **proposals** on copies.

## Required review and exclusions

Never transform matching labels or external QIDs into approved local KQ identity. Only the Kit and domain owner can register new canonical revisions after their exact contract checks.

The canonical source is each owner workspace in `C:\mycode\Kristal\locals`. `kristal-public` is a derived hosted read surface, never a place for semantic corrections. diK's federated semantic key is `(namespace_id, KQ/KP)`; bare `KQ1001` is ambiguous. Wikidata Q/P are external, reviewed links, not replacement Kristal IDs. Labels, meanings, source provenance and additive revision history remain retrievable.

Manager `audit-local-public` compares declared canonical bytes and sync-manifest scope, not semantic correctness. Excluded local files stay excluded. A candidate can move through Kit private staging and C3 only after exact owner decisions; independent C1/C2 plus exact commit/policy approval are required for public push. No direct public edits, Git push or RuntimeSet activation are allowed by this note.
