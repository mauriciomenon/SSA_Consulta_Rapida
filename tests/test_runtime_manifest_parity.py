"""Coverage gate: runtime dependency lists must not drift from pyproject.

This checks NAME COVERAGE (every direct runtime dependency of
pyproject.toml must appear in each manifest) and filelock version parity because
armazenamento/database_lock.py imports it and REL-01 shipped a frozen
venv without it.
"""

import re
try:
    import tomllib
except ImportError:  # Python <3.11
    import tomli as tomllib  # ty: ignore[unresolved-import]
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


def test_filelock_version_matches_pyproject_in_every_manifest():
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    expected = next(requirement for requirement in dependencies if requirement.startswith("filelock>="))
    for manifest in RUNTIME_MANIFESTS:
        lines = manifest.read_text(encoding="utf-8").splitlines()
        assert expected in {line.strip() for line in lines}, f"{manifest} deve declarar {expected}"
