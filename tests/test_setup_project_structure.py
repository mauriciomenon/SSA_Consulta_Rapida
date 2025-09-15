"""Guard test to ensure setup_project_structure remains available.

Prevents silent removal/regression of the utility required by main.py.
"""
from utils import setup_project_structure


def test_setup_project_structure_basics(tmp_path):
    r = setup_project_structure.setup_dirs(base_path=str(tmp_path))
    # Must succeed without fatal errors
    assert r.ok
    # At least one directory should have been created on a fresh tmp
    assert r.created, "Esperado que crie diretórios em ambiente novo"
    assert setup_project_structure.validate(str(tmp_path))
