# gui/helpers/formatting_helpers.py
# Pure formatting helper functions

import re
import html
import math
import pandas as pd


def normalize_chunk_for_parse(chunk: str) -> list[str]:
    """
    Normalize and split search chunk into terms.

    Splits ONLY by commas (no logical operators).
    All terms are required (AND logic in general search).

    Args:
        chunk: Raw search string

    Returns:
        List of normalized terms
    """
    if not chunk:
        return []
    cleaned = str(chunk).strip()
    # Replace em-dash and en-dash with regular dash for consistency
    cleaned = cleaned.replace('–', '-').replace('—', '-')
    # Split by commas only
    tokens = [term.strip() for term in cleaned.split(',') if term.strip()]
    return tokens


def format_search_display(chunks: list[list[str]]) -> str:
    """
    Format search terms for display in search input.

    Always single chunk (no OU splitting), comma-separated terms.
    All terms are required (AND logic).

    Args:
        chunks: List of chunks (typically single chunk)

    Returns:
        Comma-separated string for display
    """
    if not chunks:
        return ""
    # Since we always have single chunk, return first chunk as comma-separated
    if chunks and chunks[0]:
        return ', '.join(chunks[0])
    return ""


def format_value_for_display(value, col=None):
    """
    Format value removing NaN/None/nan and applying column-specific formatting.

    Args:
        value: Value to format
        col: Optional column name for specific formatting

    Returns:
        Formatted string, empty if null
    """
    # Remove null values
    if pd.isna(value) or value is None:
        return ""

    # Convert to string
    text = str(value)

    # Remove variations of nan/none
    if text.lower() in ('nan', 'none', 'nat', '<na>'):
        return ""

    # Colunas de semana: sempre inteiro (sem .0)
    if col and col.lower().startswith('semana'):
        try:
            num = float(text)
            if math.isnan(num):
                return ""
            return str(int(round(num)))
        except (ValueError, TypeError):
            return text.strip()

    # Column-specific formatting
    if col == 'numero_ssa':
        try:
            return str(int(float(text)))
        except (ValueError, TypeError):
            return text

    return text.strip()


def highlight_text(text: str, terms: list[str],
                  bg_color: str = 'yellow', font_weight: str = 'bold') -> str:
    """
    Apply HTML highlight to terms found in text.

    Args:
        text: Text to highlight
        terms: List of terms to highlight
        bg_color: Background color for highlight (default: yellow)
        font_weight: Font weight for highlight (default: bold)

    Returns:
        HTML string with highlighted terms
    """
    if not text or not terms:
        return text

    # Escape HTML
    text_escaped = html.escape(str(text))

    # Apply highlight for each term
    for term in terms:
        if not term:
            continue
        # Case-insensitive search
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text_escaped = pattern.sub(
            lambda m: f'<span style="background-color: {bg_color}; font-weight: {font_weight};">{m.group()}</span>',
            text_escaped
        )

    return text_escaped
