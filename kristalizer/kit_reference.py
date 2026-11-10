"""Locate and validate one independently installed Kristal Authoring Kit.

No Kit sources, schemas or templates are bundled or copied into Kristalizer.
Fail closed on ambiguous/invalid configuration or an unqualified interface.
"""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "kristalizer-config.json"
KIT_DIRNAME = "Kristal-Authoring-Kit"
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-draft\.(\d+))?$", re.I)


def _script(reference):
    path = Path(reference).expanduser().resolve()
    return path if path.name == "kristal.py" else path / "tools" / "kristal.py"


def locate_kit(explicit=None, *, root=None, environ=None, config=None):
    """Precedence: explicit > environment > config > canonical sibling. No fallback
    after a selected source turns out invalid. No network download, no vendoring.
    """
    root = Path(root).resolve() if root is not None else ROOT
    env = os.environ if environ is None else environ
    config = root / "kristalizer-config.json" if config is None else Path(config)
    if explicit is not None and str(explicit).strip():
        return _script(explicit)
    env_values = [env.get(k, "").strip() for k in ("KRISTAL_AUTHORING_KIT_HOME", "KRISTAL_AUTHORING_KIT")]
    env_values = [x for x in env_values if x]
    if len(set(map(lambda s: str(_script(s)), env_values))) > 1:
        raise ValueError("Conflicting Kristal Authoring Kit environment variables")
    if env_values:
        return _script(env_values[0])
    if config.exists():
        conf = json.loads(config.read_text(encoding="utf-8-sig"))
        if not isinstance(conf, dict):
            raise ValueError("Invalid Kristalizer config: expected JSON object")
        val = conf.get("kit")
        if isinstance(val, str) and val.strip():
            return _script(val)
    # One explicit conventional sibling location, not a recursive search that
    # might silently select an unrelated/stale installation.
    return root.parent / KIT_DIRNAME / "tools" / "kristal.py"


def inspect_kit(reference, *, framework=None):
    """Read-only safety / contract preflight. Reevaluate at each build."""
    script = _script(reference)
    if script.name != "kristal.py" or script.parent.name != "tools":
        raise ValueError("Select the canonical Authoring Kit directory or tools/kristal.py")
    script = script.resolve()
    kit_root = script.parent.parent
    if kit_root.is_relative_to(ROOT / "vendor"):
        raise ValueError("The obsolete embedded vendor Kit is forbidden; configure the canonical external Kit")
    if kit_root == ROOT or kit_root.is_relative_to(ROOT):
        raise ValueError("The Authoring Kit must be installed separately from Kristalizer")
    if not script.is_file():
        raise FileNotFoundError(f"External Kristal Authoring Kit missing: {script}")
    version_file = kit_root / "VERSION"
    pin_file = kit_root / "contracts" / "v11-framework-pin.json"
    if not version_file.is_file() or not pin_file.is_file():
        raise ValueError("Not a complete canonical Authoring Kit (VERSION or v11 pin absent)")
    version = version_file.read_text(encoding="utf-8-sig").strip()
    match = VERSION_PATTERN.fullmatch(version)
    if not match:
        raise ValueError(f"Unrecognized Kit version {version!r}; review compatibility before using it")
    major, minor, patch = map(int, match.groups()[:3]); draft = match.group(4)
    # Only the exact v4 draft.4 producer / consumer pair has been checked here.
    # A later version requires an explicit compatibility matrix and new fixtures,
    # not a semver shortcut that authorizes unknown changes.
    if version != "4.0.0-draft.4":
        raise ValueError(f"Kit {version} not qualified for this integration (requires pinned 4.0.0-draft.4)")
    pin = json.loads(pin_file.read_text(encoding="utf-8-sig"))
    fw_version = pin.get("version", "")
    if (pin.get("profile") != "kristal-integration-framework-pin/v11.0-draft.4"
            or fw_version != "11.0.0-draft.4"):
        raise ValueError(f"Unsupported Framework contract pin {fw_version!r}; exact draft.4 profile required")
    pinned = pin.get("files")
    required = {"VERSION", "schemas/v11/kristal-identity-registry.schema.json",
                "schemas/v11/kristal-semantic-graph.schema.json",
                "schemas/v11/kristal-external-crosswalk.schema.json",
                "schemas/v11/kristal-dictionary-catalog.schema.json",
                "tools/v11/validate_v11.py", "tools/v11/interop_preflight.py"}
    if (not isinstance(pinned, dict) or not required.issubset(pinned)
            or len(pinned) != 13):
        raise ValueError("Incomplete pinned Framework source inventory")
    for name, value in pinned.items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or "\\" in name or not re.fullmatch(r"[a-f0-9]{64}", str(value)):
            raise ValueError("Unsafe or incomplete Framework pin entry: " + str(name))
    framework_verified = False
    if framework is not None:
        fw = Path(framework).expanduser().resolve()
        vfile = fw / "VERSION"
        if not vfile.is_file() or vfile.read_text(encoding="utf-8").strip() != fw_version:
            raise ValueError("Framework source does not match pinned version")
        for name, digest in pinned.items():
            source = (fw / name).resolve()
            if not source.is_relative_to(fw) or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError("Framework source pin drift: " + name)
        framework_verified = True
    src = script.read_text(encoding="utf-8-sig")
    code_version = re.search(r"^KIT_VERSION\s*=\s*['\"]([^'\"]+)['\"]",src,re.M)
    if not code_version or code_version.group(1) != version:
        raise ValueError("Kit VERSION and tools/kristal.py KIT_VERSION do not match")
    # Query the actual CLI interface, not a string that might only appear in a comment.
    required = ("check-v11", "check", "build-v9", "publish-v9", "activate-v9", "register-artifact", "enable-v11")
    try:
        result = subprocess.run([sys.executable, str(script), "--help"], cwd=str(kit_root),
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Could not inspect Authoring Kit CLI: {exc}") from exc
    if result.returncode:
        raise ValueError("Authoring Kit --help failed: " + (result.stderr or result.stdout)[-800:])
    choices = re.search(r"\{([^}]+)\}", result.stdout)
    commands = set(choices.group(1).split(",")) if choices else set()
    missing = [cmd for cmd in required if cmd not in commands]
    if missing:
        raise ValueError("Kit CLI lacks required commands: " + ", ".join(missing))
    fingerprints = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key,path in
                    (("script", script), ("version", version_file), ("pin", pin_file))}
    return {"script": str(script), "root": str(kit_root), "version": version,
            "framework_pin": fw_version, "source": "external-canonical", "bundled": False,
            "framework_source_checked": framework_verified,
            "scope": "local contract preflight; not cross-product qualification, release authorization or deployment",
            "fingerprints_sha256": fingerprints}


def resolve_kit(explicit=None, *, framework=None):
    """Resolve one usable external Kit; optional exact Framework source validation.

    An explicitly set `KRISTAL_FRAMEWORK_ROOT` also requests source checking
    before a build. No network discovery or implicit pin promotion is performed.
    """
    if framework is None:
        framework = os.environ.get("KRISTAL_FRAMEWORK_ROOT") or None
    return inspect_kit(locate_kit(explicit), framework=framework)
