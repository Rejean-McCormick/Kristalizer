# Branch 02 — Kristalizer proposals into canonical Kit authoring

**State:** local Kit 4.0.0-draft.4 source preflight and staged workflow checks; *not* global semantic approval, production migration or public publishing.

## Opt-in external Kit verification

```bash
python kristalizer.py kit-status --kit ../Authoring-Kit --framework ../Framework
```

`kit-status` verifies the **exact Kit 4.0.0-draft.4**, its CLI command surface, and its declared Framework 11.0.0-draft.4 compatibility pin. When `--framework` is explicitly supplied (or `KRISTAL_FRAMEWORK_ROOT` is configured), each of 13 actual Framework source files must match the Kit's digest. Without Framework source, the report sets `framework_source_checked: false`: a local pin declaration is not independent qualification. Unknown future Kit versions fail closed pending an approved compatibility matrix; no permissive "any 4.x" assumption remains.

The existing `scan`, `stage` and `build` phases retain their source-isolation and reviewed mapping rules: accepted KS evidence is required before any exact-match candidate can be staged. `build --publish --activate` operates **only on staged copies**, using local Kit semantics. It is not GitHub or public publication authorization.

## Required bilateral acceptance

- Exact Framework/Kit versions and hashes must be checked before a staged write.
- Only reviewed source evidence and authorized mapping decisions may lead to Kit imports. Identity collisions, unapproved QIDs and incomplete evidence must remain rejected.
- The receiving Kit must independently revalidate all inputs under its transaction model; the orchestration report is not equivalent to a Kit commit.
- The single external Kit must remain an independent owner repository. No vendored Kit restoration, automatic fetch or hidden path fallback.

**To qualify further:** test one real Kristalizer staged crosswalk against a copied Kit semantic workspace and record both sides' terminal receipts without any effect on original source data. See the central Branch 02 handoff report for exact unresolved owner approvals.
