import os, pandas as pd, tempfile
from extracao.extractor import read_report
import extracao.extractor as ex

def mock_load_mappings():
    return {alias: canonical for canonical, aliases in {
      "numero_ssa": ["Nº SSA"],
      "localizacao": ["Local"],
      "descricao_ssa": ["Descrição da SSA"],
      "data_cadastro": ["Emitida Em"]
    }.items() for alias in aliases}

ex._load_column_mappings = mock_load_mappings

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, 'relatorio_teste.xlsx')
    df = pd.DataFrame({
        'Nº SSA': [101,102],
        'Local': ['Sala A','Sala B'],
        'Descrição da SSA':['Problema','Falha'],
        'Emitida Em':['01/07/2025','15/07/2025'],
        'Coluna Inutil':[None,None]
    })
    with pd.ExcelWriter(path, engine='openpyxl') as w:
        df.to_excel(w, index=False, startrow=1)
    out, _ = read_report(path)
    print(out.dtypes)
    print('is dt?', pd.api.types.is_datetime64_any_dtype(out['data_cadastro']))
    print(out.head())
