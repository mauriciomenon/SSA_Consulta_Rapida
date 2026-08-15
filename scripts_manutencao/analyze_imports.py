import ast
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {".git", "__pycache__", "LocalTemp", "venv", ".venv", ".idea", ".vscode"}
KNOWN_TOP = {
    "core",
    "gui",
    "interface",
    "armazenamento",
    "extracao",
    "exportacao",
    "utils",
    "config",
}


def iter_py_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def top_pkg(module: str) -> str | None:
    if not module:
        return None
    head = module.split(".", 1)[0]
    return head if head in KNOWN_TOP else None


def build_graph():
    edges = defaultdict(set)  # pkg -> set[pkg]
    files_by_pkg = defaultdict(list)
    for path in iter_py_files(ROOT):
        rel = path.relative_to(ROOT)
        pkg = rel.parts[0]
        if pkg not in KNOWN_TOP:
            continue
        files_by_pkg[pkg].append(rel.as_posix())
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    tp = top_pkg(alias.name)
                    if tp and tp != pkg:
                        edges[pkg].add(tp)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                tp = top_pkg(mod)
                if tp and tp != pkg:
                    edges[pkg].add(tp)
    return edges, files_by_pkg


def find_cycles(edges):
    cycles = []
    temp = set()
    perm = set()
    stack = []

    def dfs(u: str):
        temp.add(u)
        stack.append(u)
        for v in edges.get(u, ()):
            if v not in temp and v not in perm:
                dfs(v)
            elif v in temp:
                # found a cycle
                i = stack.index(v)
                cycles.append(stack[i:] + [v])
        stack.pop()
        temp.remove(u)
        perm.add(u)

    for node in set(edges) | {v for s in edges.values() for v in s}:
        if node not in temp and node not in perm:
            dfs(node)
    return cycles


def main():
    edges, files_by_pkg = build_graph()
    print("== Package-level Import Graph ==")
    for pkg in sorted(KNOWN_TOP):
        deps = sorted(edges.get(pkg, ()))
        print(f"{pkg:15} -> {', '.join(deps) if deps else '-'}")

    cycles = find_cycles(edges)
    print("\n== Cycles ==")
    if not cycles:
        print("None")
    else:
        for c in cycles:
            print(" -> ".join(c))

    # Simple layer checks
    violations = []
    for src, tgts in edges.items():
        for tgt in tgts:
            # core should not depend on gui or interface
            if src == "core" and tgt in {"gui", "interface"}:
                violations.append((src, tgt, "core must not import GUI layers"))
            # armazenamento (storage) should not depend on gui or interface
            if src == "armazenamento" and tgt in {"gui", "interface"}:
                violations.append((src, tgt, "storage must not import GUI layers"))
            # utils should be bottom-only
            if src == "utils" and tgt in {
                "core",
                "gui",
                "interface",
                "armazenamento",
                "extracao",
                "exportacao",
            }:
                violations.append(
                    (src, tgt, "utils should not import domain/application layers")
                )
    print("\n== Layer Violations (heuristic) ==")
    if not violations:
        print("None")
    else:
        for s, t, msg in violations:
            print(f"{s} -> {t}: {msg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
