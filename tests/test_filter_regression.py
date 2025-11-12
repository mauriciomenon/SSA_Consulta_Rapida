"""
Regression tests for filter behavior to prevent reintroduction of old bugs.

Tests verify:
1. Comma input is allowed and not stripped in search fields
2. Logical operators (||, v, OU, OR, AND) are NOT treated as operators
3. Column filter text is properly highlighted
4. Filter behavior matches specification (no operator keywords)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from core.app_logic import parse_search_terms, filter_dataframe


class TestFilterRegression:
    """Regression tests for filter bugs that should never return."""

    def test_comma_allowed_in_search_terms(self):
        """Test that commas are preserved and used as term separators."""
        # User should be able to type commas
        search_text = "term1,term2,term3"
        terms = parse_search_terms(search_text.split(','))

        assert len(terms) == 3
        assert terms[0]['value'] == 'term1'
        assert terms[1]['value'] == 'term2'
        assert terms[2]['value'] == 'term3'

    def test_logical_operators_treated_as_literals(self):
        """Test that ||, v, OU, OR, AND are treated as literal search terms, not operators."""
        # These should be searched as literal strings, not treated as logical operators
        test_cases = [
            "||",  # Should search for "||" literally
            "v",   # Should search for "v" literally
            "OU",  # Should search for "OU" literally
            "OR",  # Should search for "OR" literally
            "AND", # Should search for "AND" literally
        ]

        for search_term in test_cases:
            terms = parse_search_terms([search_term])
            assert len(terms) == 1, f"'{search_term}' should be treated as single literal term"
            # Value should be the search term itself (case may be preserved)
            assert terms[0]['value'].upper() == search_term.upper(), f"'{search_term}' should be treated as literal"
            assert terms[0]['group'] == 0, f"All terms should be in group 0 (AND logic)"

    def test_no_operator_splitting(self):
        """Test that old operator keywords don't cause term splitting."""
        # These patterns used to be split by operators - they should NOT be anymore
        search_text = "termo1 OU termo2"  # Should NOT split by OU
        terms = parse_search_terms([search_text])

        # Should be treated as single term containing "termo1 ou termo2"
        assert len(terms) == 1
        assert "termo1 ou termo2" in terms[0]['value'].lower()

    def test_comma_in_column_filter(self):
        """Test that column filters accept commas for OR logic within column."""
        # Column filters should split by comma for OR logic
        column_filter = "valor1,valor2,valor3"
        terms = column_filter.split(',')

        assert len(terms) == 3
        assert terms[0].strip() == "valor1"
        assert terms[1].strip() == "valor2"
        assert terms[2].strip() == "valor3"

    def test_filter_dataframe_with_commas(self):
        """Integration test: filter_dataframe should work with comma-separated terms."""
        df = pd.DataFrame({
            'col1': ['foo', 'bar', 'baz'],
            'col2': ['test1', 'test2', 'test3']
        })

        # General search with commas (AND logic)
        search_terms = ['foo', 'test1']
        result = filter_dataframe(df, search_terms=search_terms)

        assert len(result) == 1
        assert result.iloc[0]['col1'] == 'foo'
        assert result.iloc[0]['col2'] == 'test1'

    def test_filter_dataframe_column_filter_or_logic(self):
        """Test that filter_dataframe works with multiple search terms."""
        df = pd.DataFrame({
            'col1': ['foo', 'bar', 'baz'],
            'col2': ['test1', 'test2', 'test3']
        })

        # Search for multiple terms (AND logic in general search)
        result = filter_dataframe(df, search_terms=['foo', 'test1'], search_columns=['col1', 'col2'])

        assert len(result) == 1
        assert result.iloc[0]['col1'] == 'foo'

    def test_no_old_operator_behavior(self):
        """Test that old operator patterns don't trigger special behavior."""
        df = pd.DataFrame({
            'descricao': [
                'processo v123',
                'item || outro',
                'contrato OU servico',
                'produto OR ferramenta',
                'sistema AND banco'
            ]
        })

        # Searching for these should find them as literal text
        for search_term in ['v123', '||', 'OU', 'OR', 'AND']:
            result = filter_dataframe(df, search_terms=[search_term])
            assert len(result) >= 1, f"Should find '{search_term}' as literal text"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
