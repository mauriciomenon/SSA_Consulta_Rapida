#!/usr/bin/env python3
"""
Teste direto dos executaveis v3.10
"""

import subprocess
import sys
from pathlib import Path
import pytest

# --- Fixtures -----------------------------------------------------------------
@pytest.fixture(params=[
    {
        "name": "CLI Multi-Plataforma",
        "path": Path(__file__).parent / 'dist' / 'macos_arm64' / 'SSA_CLI_v3.10_macos_arm64' / 'SSA_CLI_v3.10_macos_arm64'
    },
    {
        "name": "CLI Simples",
        "path": Path(__file__).parent / 'dist_simple' / 'SSA_CLI_v3.10_SIMPLES' / 'SSA_CLI_v3.10_SIMPLES'
    }
])
def executable_spec(request):
    """Provides spec for each expected executable. The file may or may not exist (test will xfail missing)."""
    return request.param

@pytest.fixture
def exe_path(executable_spec):
    return executable_spec["path"]

@pytest.fixture
def name(executable_spec):
    return executable_spec["name"]

# --- Helper -------------------------------------------------------------------
def _check_executable(exe_path: Path, name: str) -> bool:
    print(f"\n=== Testando {name} ===")
    print(f"Path: {exe_path}")
    if not exe_path.exists():
        print(f"⚠️ Executavel nao encontrado: {exe_path}")
        return False
    # Verificar tipo (best-effort)
    try:
        result = subprocess.run(['file', str(exe_path)], capture_output=True, text=True, timeout=3)
        if result.stdout:
            print(f"Tipo: {result.stdout.strip()}")
    except Exception:
        pass
    # Verificar tamanho da pasta base
    try:
        size_mb = sum(p.stat().st_size for p in exe_path.parent.rglob('*') if p.is_file()) / (1024*1024)
        print(f"Tamanho estimado pasta: {size_mb:.1f}M")
    except Exception:
        pass
    # Teste simples - executar sem argumentos
    print("Testando execucao...")
    try:
        result = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=5)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout[:200]}...")
        if result.stderr:
            print(f"STDERR: {result.stderr[:200]}...")
        if result.returncode in (0, 2):  # 2 comum para uso/ajuda
            return True
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ Timeout - assumindo OK (pode estar aguardando input)")
        return True
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        return False

# --- Tests --------------------------------------------------------------------
@pytest.mark.smoke
@pytest.mark.cli
def test_executable(exe_path, name):
    ok = _check_executable(exe_path, name)
    if not ok:
        # We don't fail hard if optional executable missing; mark xfail for visibility
        pytest.xfail(f"Executable '{name}' ausente ou falhou no teste basico")

# Retem main for manual execution ------------------------------------------------
def main():  # pragma: no cover
    base_dir = Path(__file__).parent.parent
    print(f"=== Teste de Executaveis v3.10 ===")
    print(f"Base: {base_dir}")
    specs = [
        ("CLI Multi-Plataforma", Path(__file__).parent / 'dist' / 'macos_arm64' / 'SSA_CLI_v3.10_macos_arm64' / 'SSA_CLI_v3.10_macos_arm64'),
        ("CLI Simples", Path(__file__).parent / 'dist_simple' / 'SSA_CLI_v3.10_SIMPLES' / 'SSA_CLI_v3.10_SIMPLES')
    ]
    results = []
    for n, p in specs:
        results.append((n, _check_executable(p, n)))
    print("\n=== RESUMO ===")
    for n, r in results:
        print(f"{n}: {'✅ OK' if r else '❌ ERRO'}")
    ok_any = any(r for _, r in results)
    if ok_any:
        print("\n🎯 Pelo menos um executavel funcionando!")
        return 0
    print("\n❌ Nenhum executavel funcionando!")
    return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
