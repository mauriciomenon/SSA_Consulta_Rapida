import json
import os
from typing import Optional


def get_app_version(project_root: Optional[str] = None) -> str:
    """Le a versao do arquivo config/version.json.

    Fallback: retorna '0.0.0' se indisponivel.
    """
    try:
        root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        version_file = os.path.join(root, 'config', 'version.json')
        with open(version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return str(data.get('version') or data.get('version_short') or data.get('appVersion') or '0.0.0')
    except Exception:
        return '0.0.0'


def get_app_version_long(project_root: Optional[str] = None) -> str:
    """Le a versao longa (texto) do arquivo config/version.json.

    Fallback: retorna string vazia se indisponivel.
    """
    try:
        root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        version_file = os.path.join(root, 'config', 'version.json')
        with open(version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return str(data.get('version_long') or '')
    except Exception:
        return ''
