# clean_pycache.py
import os
import shutil
from pathlib import Path

def clean_pycache(root_dir: str = "."):
    """Remove todas as pastas __pycache__ recursivamente."""
    root_path = Path(root_dir)
    for pycache_dir in root_path.rglob("__pycache__"):
        if pycache_dir.is_dir():
            print(f"Removendo: {pycache_dir}")
            try:
                shutil.rmtree(pycache_dir)
            except Exception as e:
                print(f"Erro ao remover {pycache_dir}: {e}")

    print("Remoção de __pycache__ concluída.")

if __name__ == "__main__":
    clean_pycache()