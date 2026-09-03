"""Gate: runtime manifests must not drift from pyproject direct dependencies.

Regression for REL-01: `armazenamento/database_lock.py` imports `filelock`,
`pyproject.toml` declares it, but the runtime manifests omitted it - the
frozen release venv failed to import the database module.
"""

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RUNTIME_MANIFESTS = (
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "launchers/platforms/debian_amd64/requirements.txt",
    PROJECT_ROOT / "launchers/platforms/debian_arm64/requirements.txt",
    PROJECT_ROOT / "launchers/platforms/macos_arm64/requirements.txt",
    PROJECT_ROOT / "launchers/platforms/windows_amd64/requirements.txt",
)

_REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _canonical(name: str) -> str:
    return name.lower().replace("_", "-")


def _pyproject_runtime_deps() -> set[str]:
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    dependencies = data["project"]["dependencies"]
    names = set()
    for requirement in dependencies:
        match = _REQUIREMENT_NAME_RE.match(requirement)
        if match:
            names.add(_canonical(match.group(1)))
    assert names, "pyproject.toml [project] dependencies must not be empty"
    return names


def _manifest_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#") or not line.strip():
            continue
        match = _REQUIREMENT_NAME_RE.match(line)
        if match:
            names.add(_canonical(match.group(1)))
    return names


def test_requirements_txt_covers_pyproject_runtime_deps():
    expected = _pyproject_runtime_deps()
    actual = _manifest_names(RUNTIME_MANIFESTS[0])
    missing = expected - actual
    assert not missing, f"requirements.txt missing runtime deps: {sorted(missing)}"


def test_platform_manifests_cover_pyproject_runtime_deps():
    expected = _pyproject_runtime_deps()
    for manifest in RUNTIME_MANIFESTS[1:]:
        actual = _manifest_names(manifest)
        missing = expected - actual
        assert not missing, f"{manifest.name} missing runtime deps: {sorted(missing)}"


def test_filelock_present_everywhere():
    assert "filelock" in _manifest_names(RUNTIME_MANIFESTS[0])
    for manifest in RUNTIME_MANIFESTS[1:]:
        assert "filelock" in _manifest_names(manifest), manifest
