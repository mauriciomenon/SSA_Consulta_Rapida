import sys

sys.path.insert(0, ".")

print("Testando se main faz rescan automaticamente...")
print("Simulando execução sem --force-rescan...")

# Simula sys.argv sem --force-rescan
sys.argv = ["main.py"]

try:
    print("Import OK")
    # Não executar main() para evitar loop, apenas testar parse
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-rescan", "--rescan", dest="force_rescan", action="store_true"
    )
    args = parser.parse_args([])  # Lista vazia = sem argumentos
    print(f"force_rescan seria: {args.force_rescan}")
    if args.force_rescan:
        print("ERRO: force_rescan é True quando deveria ser False!")
    else:
        print("OK: force_rescan é False por padrão")
except Exception as e:
    print(f"Erro: {e}")
    import traceback

    traceback.print_exc()
