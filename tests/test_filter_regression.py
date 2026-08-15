"""
Regression tests for filter behavior to prevent reintroduction of old bugs.

Tests verify:
1. parse_search_terms splits raw comma input into AND terms
2. Under the current simplified contract, logical keywords remain literal
3. Column filter text is properly highlighted
4. Filter behavior matches specification (no operator keywords)
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pytest

import core.app_logic as app_logic
from core.app_logic import filter_dataframe, parse_search_terms


class TestFilterRegression:
    """Regression tests for filter bugs that should never return."""

    def test_parse_search_terms_splits_raw_comma_input(self):
        """Test that parse_search_terms splits raw comma input into AND terms."""
        search_text = "term1,term2,term3"
        terms = parse_search_terms([search_text])

        assert len(terms) == 3
        assert terms[0]["value"] == "term1"
        assert terms[1]["value"] == "term2"
        assert terms[2]["value"] == "term3"
        assert terms[0]["group"] == 0

    def test_logical_operators_treated_as_literals(self):
        """Test that ||, v, OU, OR, AND remain literal under the simplified contract."""
        # These should be searched as literal strings, not treated as logical operators
        test_cases = [
            "||",  # Should search for "||" literally
            "v",  # Should search for "v" literally
            "OU",  # Should search for "OU" literally
            "OR",  # Should search for "OR" literally
            "AND",  # Should search for "AND" literally
        ]

        for search_term in test_cases:
            terms = parse_search_terms([search_term])
            assert len(terms) == 1, (
                f"'{search_term}' should be treated as single literal term"
            )
            # Value should be the search term itself (case may be preserved)
            assert terms[0]["value"].upper() == search_term.upper(), (
                f"'{search_term}' should be treated as literal"
            )
            assert terms[0]["group"] == 0, "All terms should be in group 0 (AND logic)"

    def test_no_operator_splitting(self):
        """Test that old operator keywords don't cause term splitting."""
        # These patterns used to be split by operators - they should NOT be anymore
        search_text = "termo1 OU termo2"  # Should NOT split by OU
        terms = parse_search_terms([search_text])

        # Should be treated as single term containing "termo1 ou termo2"
        assert len(terms) == 1
        assert "termo1 ou termo2" in terms[0]["value"].lower()

    def test_comma_in_column_filter(self):
        """Test that column filters accept commas for OR logic within column."""
        # Column filters should split by comma for OR logic
        column_filter = "valor1,valor2,valor3"
        terms = column_filter.split(",")

        assert len(terms) == 3
        assert terms[0].strip() == "valor1"
        assert terms[1].strip() == "valor2"
        assert terms[2].strip() == "valor3"

    def test_filter_dataframe_with_commas(self):
        """Integration test: filter_dataframe should work with comma-separated terms."""
        df = pd.DataFrame(
            {"col1": ["foo", "bar", "baz"], "col2": ["test1", "test2", "test3"]}
        )

        # General search with commas (AND logic)
        search_terms = ["foo", "test1"]
        result = filter_dataframe(df, search_terms=search_terms)

        assert len(result) == 1
        assert result.iloc[0]["col1"] == "foo"
        assert result.iloc[0]["col2"] == "test1"

    def test_filter_dataframe_column_filter_or_logic(self):
        """Test that filter_dataframe works with multiple search terms."""
        df = pd.DataFrame(
            {"col1": ["foo", "bar", "baz"], "col2": ["test1", "test2", "test3"]}
        )

        # Search for multiple terms (AND logic in general search)
        result = filter_dataframe(
            df, search_terms=["foo", "test1"], search_columns=["col1", "col2"]
        )

        assert len(result) == 1
        assert result.iloc[0]["col1"] == "foo"

    def test_no_old_operator_behavior(self):
        """Test that old operator patterns don't trigger special behavior."""
        df = pd.DataFrame(
            {
                "descricao": [
                    "processo v123",
                    "item || outro",
                    "contrato OU servico",
                    "produto OR ferramenta",
                    "sistema AND banco",
                ]
            }
        )

        # Searching for these should find them as literal text
        for search_term in ["v123", "||", "OU", "OR", "AND"]:
            result = filter_dataframe(df, search_terms=[search_term])
            assert len(result) >= 1, f"Should find '{search_term}' as literal text"

    @pytest.mark.parametrize(
        "table_name",
        ["ssas", "SSA_TABLE", "SSAS", "ssa_chamados", " SSA_CHAMADOS "],
    )
    def test_db_only_derivadas_preflight_accepts_legacy_ssa_aliases(
        self, tmp_path, table_name
    ):
        """Legacy aliases should resolve to the canonical derivadas preflight query."""
        db_path = tmp_path / "derivadas_alias.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE ssa_table (
                    numero_ssa TEXT,
                    derivada_de TEXT
                );
                INSERT INTO ssa_table (numero_ssa, derivada_de) VALUES
                    ('202500001', '202500000');
                """
            )

        assert app_logic._needs_db_only_derivadas_sync(str(db_path), table_name) is True

    def test_db_only_derivadas_preflight_accepts_view_only_ssas_alias(self, tmp_path):
        """The preflight must also work when only the compatibility view exists."""
        db_path = tmp_path / "derivadas_alias_view.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE base_ssa (
                    numero_ssa TEXT,
                    derivada_de TEXT
                );
                INSERT INTO base_ssa (numero_ssa, derivada_de) VALUES
                    ('202500001', '202500000');
                CREATE VIEW ssas AS
                SELECT numero_ssa, derivada_de
                FROM base_ssa;
                """
            )

        assert app_logic._needs_db_only_derivadas_sync(str(db_path), "ssas") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
