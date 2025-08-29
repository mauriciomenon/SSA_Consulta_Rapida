import json
import os


def test_readme_exists_and_has_core_sections():
    assert os.path.exists('README.md')
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()
    # Check some key headings/phrases
    assert '# SSA_Consulta_Rapida' in content
    assert 'Instalação' in content
    assert 'Uso' in content
    assert 'Testes' in content


def test_changelog_full_exists_and_has_history():
    path = os.path.join('docs_saida', 'CHANGELOG_IMPLEMENTACOES.md')
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Must contain multiple dated sections and core topics
    assert '2025-08-' in content or '2025-07-' in content
    assert 'column_priority.json' in content
    assert 'GUI' in content or 'CLI' in content


def test_column_priority_has_required_keys_and_values():
    with open(os.path.join('config', 'column_priority.json'), 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    # Required keys
    for key in ['essential', 'always_visible', 'priority_order', 'short_labels', 'fixed_widths', 'hidden_by_default']:
        assert key in cfg
    # Essential minimal content
    assert 'numero_ssa' in cfg['essential']
    assert 'situacao' in cfg['always_visible']
    assert isinstance(cfg['short_labels'], dict) and len(cfg['short_labels']) >= 5
    assert isinstance(cfg['fixed_widths'], dict) and 'numero_ssa' in cfg['fixed_widths']
