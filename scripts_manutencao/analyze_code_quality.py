import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "LocalTemp",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    "temp",
}


def iter_py_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def check_unused_imports():
    """Detect potentially unused imports (simple heuristic)"""
    issues = []
    for path in iter_py_files(ROOT):
        try:
            code = path.read_text(encoding="utf-8")
            tree = ast.parse(code, filename=str(path))
        except Exception:
            continue

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name)

        # Simple check: is the imported name mentioned elsewhere in code?
        for imp in imports:
            if imp == "*":
                continue
            # Count occurrences (excluding import line itself)
            count = code.count(imp)
            # Heuristic: if it appears only once (the import), might be unused
            if count == 1:
                rel = path.relative_to(ROOT)
                issues.append(f"{rel}: possibly unused import '{imp}'")

    return issues


def check_shared_purity():
    """Verify shared/ doesn't import from app layers"""
    violations = []
    shared_dir = ROOT / "shared"
    if not shared_dir.exists():
        return ["shared/ directory not found"]

    forbidden = {
        "core",
        "gui",
        "interface",
        "armazenamento",
        "extracao",
        "exportacao",
        "utils",
    }

    for path in shared_dir.glob("**/*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    if pkg in forbidden:
                        violations.append(f"{path.name}: imports {pkg}")
            elif isinstance(node, ast.ImportFrom):
                pkg = (node.module or "").split(".")[0]
                if pkg in forbidden:
                    violations.append(f"{path.name}: imports from {pkg}")

    return violations


def check_backward_compat():
    """Verify core.numero_ssa and core.date_utils still export expected symbols"""
    issues = []

    # Check core.numero_ssa
    numero_ssa_path = ROOT / "core" / "numero_ssa.py"
    if numero_ssa_path.exists():
        try:
            tree = ast.parse(numero_ssa_path.read_text(encoding="utf-8"))
            exports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        exports.add(alias.name)

            expected = {"normalize_strict", "is_valid_numero_ssa", "bulk_normalize"}
            missing = expected - exports
            if missing:
                issues.append(f"core.numero_ssa missing re-exports: {missing}")
        except Exception as e:
            issues.append(f"core.numero_ssa parse error: {e}")

    # Check core.date_utils
    date_utils_path = ROOT / "core" / "date_utils.py"
    if date_utils_path.exists():
        try:
            tree = ast.parse(date_utils_path.read_text(encoding="utf-8"))
            exports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        exports.add(alias.name)

            expected = {"parse_any_date", "bulk_parse_dates"}
            missing = expected - exports
            if missing:
                issues.append(f"core.date_utils missing re-exports: {missing}")
        except Exception as e:
            issues.append(f"core.date_utils parse error: {e}")

    return issues


def check_armazenamento_independence():
    """Verify armazenamento doesn't import from core/gui/interface"""
    violations = []
    armazenamento_dir = ROOT / "armazenamento"
    if not armazenamento_dir.exists():
        return []

    forbidden = {"core", "gui", "interface", "extracao", "exportacao"}

    for path in armazenamento_dir.glob("**/*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    if pkg in forbidden:
                        violations.append(
                            f"{path.name}: imports {pkg} (armazenamento should be independent)"
                        )
            elif isinstance(node, ast.ImportFrom):
                pkg = (node.module or "").split(".")[0]
                if pkg in forbidden:
                    violations.append(
                        f"{path.name}: imports from {pkg} (armazenamento should be independent)"
                    )

    return violations


def main():
    print("=== Code Quality Analysis ===\n")

    print("1. Shared Module Purity Check")
    shared_issues = check_shared_purity()
    if shared_issues:
        print("  VIOLATIONS:")
        for issue in shared_issues:
            print(f"    - {issue}")
    else:
        print("  OK: shared/ doesn't import from app layers")

    print("\n2. Backward Compatibility Check")
    compat_issues = check_backward_compat()
    if compat_issues:
        print("  ISSUES:")
        for issue in compat_issues:
            print(f"    - {issue}")
    else:
        print("  OK: core re-exports are intact")

    print("\n3. Armazenamento Independence Check")
    armazenamento_issues = check_armazenamento_independence()
    if armazenamento_issues:
        print("  VIOLATIONS:")
        for issue in armazenamento_issues:
            print(f"    - {issue}")
    else:
        print("  OK: armazenamento is independent")

    print("\n4. Potentially Unused Imports (top 20)")
    unused = check_unused_imports()
    if unused:
        for issue in unused[:20]:
            print(f"  - {issue}")
        if len(unused) > 20:
            print(f"  ... and {len(unused) - 20} more")
    else:
        print("  None detected")

    print("\n=== Summary ===")
    total_issues = len(shared_issues) + len(compat_issues) + len(armazenamento_issues)
    if total_issues == 0:
        print("All critical checks passed!")
    else:
        print(f"Found {total_issues} critical issues")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
