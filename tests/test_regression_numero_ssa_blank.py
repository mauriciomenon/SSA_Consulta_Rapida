import io

import pandas as pd

from utils.robust_importer import import_excel_robust


def test_regression_numero_ssa_float_and_blank(tmp_path):
    """Garante que primeira linha válida (possivelmente lida como float .0) não é descartada
    quando segunda linha está em branco/None."""
    for bad in (None, "", "  "):
        df = pd.DataFrame(
            {
                "Nº SSA": [
                    "202500777",
                    bad,
                ],  # pode ser interpretado como float em alguns cenários
                "Situação": ["OK", "IGNORAR"],
            }
        )
        bio = io.BytesIO()
        df.to_excel(bio, index=False)
        bio.seek(0)
        f = tmp_path / f"case_{repr(bad).replace(' ', '_')}.xlsx"
        f.write_bytes(bio.getvalue())
        out, stats = import_excel_robust(str(f))
        assert "numero_ssa" in out.columns
        assert stats["invalid_numero_ssa_rows"] >= 1  # a linha ruim conta
        # A linha válida deve permanecer
        assert any(v == "202500777" for v in out["numero_ssa"].tolist()), (
            f"Valor valido perdido para bad={bad!r}"
        )
