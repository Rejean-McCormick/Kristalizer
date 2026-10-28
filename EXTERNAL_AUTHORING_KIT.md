# External Authoring Kit — single source of truth

Kristalizer no longer ships `vendor/Kristal-Authoring-Kit/`. The independently maintained [Kristal-Authoring-Kit](https://github.com/Rejean-McCormick/Kristal-Authoring-Kit) is the only canonical Kit installation. Kristalizer orchestrates it over its published `tools/kristal.py` command line and does **not** duplicate its code, contracts, templates, fixtures, or tests.

## Recommended placement

```text
C:\mycode\
  Kristal-Authoring-Kit\       # independent checkout; update here only
    VERSION
    contracts\v11-framework-pin.json
    tools\kristal.py
  Kristalizer\
    Kristalizer.pyw
    kristalizer\
```

Both may be installed anywhere; use the GUI **External Authoring Kit** path, `KRISTAL_AUTHORING_KIT_HOME`, or CLI `--kit PATH` to choose a non-sibling location. Pass either the Kit root directory or its `tools/kristal.py` entrypoint. The saved GUI configuration is local and not packaged. Resolution priority: explicit `--kit`, environment, local config, sibling location.

## Compatibility and safety

- Before invoking a build, the Kit must exist **outside** Kristalizer and staging, report `VERSION` `4.0.0-draft.4` or compatible 4.x, have a Framework v11 pin, and expose the expected commands. Unsupported major/Framework transitions fail closed for review.
- No network download, Git clone, install, file sync, vendored fallback, or Kit update is attempted. Keep the Kit up to date **once** in its own repository.
- `scan`, `import-decisions`, and `stage` require no Kit. `build`/`publish`/`activate` require one valid external Kit.
- Build output records the resolved canonical Kit path, Kit version, and Framework pin. Validation only checks the integration boundary, **not** comprehensive release qualification.
- All build operations still target staging copies, never the original Kristals.

Verify the dependency:

```powershell
py -3 kristalizer.py kit-status
py -3 kristalizer.py kit-status --kit "C:\mycode\Kristal-Authoring-Kit"
```

To migrate from the old ZIP: place Kristalizer in a clean directory rather than overlaying the old `vendor/`; keep the canonical Kit alongside it. If an old local `kristalizer-config.json` references a removed `vendor/` path, replace that setting with the external Kit path. The new build refuses the legacy embedded Kit.
