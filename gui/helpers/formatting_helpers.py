# gui/helpers/formatting_helpers.py
# Pure formatting helper functions

import html
import re


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
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    # Split by commas only
    tokens = [term.strip() for term in cleaned.split(",") if term.strip()]
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
        return ", ".join(chunks[0])
    return ""


def _normalize_highlight_terms(terms: list[str]) -> list[str]:
    """Normalize terms for one-pass highlight matching."""
    normalized_terms: list[str] = []
    seen_terms: set[str] = set()

    for raw_term in terms:
        escaped_term = html.escape(str(raw_term or "")).strip()
        if not escaped_term:
            continue
        term_key = escaped_term.casefold()
        if term_key in seen_terms:
            continue
        seen_terms.add(term_key)
        normalized_terms.append(escaped_term)

    normalized_terms.sort(key=len, reverse=True)
    return normalized_terms


def highlight_text(
    text: str | None,
    terms: list[str],
    bg_color: str = "yellow",
    font_weight: str = "bold",
    text_color: str | None = None,
) -> str:
    """
    Apply HTML highlight to terms found in text.

    Args:
        text: Text to highlight
        terms: List of terms to highlight
        bg_color: Background color for highlight (default: yellow)
        font_weight: Font weight for highlight (default: bold)
        text_color: Foreground color for highlight (optional)

    Returns:
        HTML string with highlighted terms
    """
    if text is None:
        return ""

    escaped_text = html.escape(str(text))
    if not terms:
        return escaped_text

    normalized_terms = _normalize_highlight_terms(terms)
    if not normalized_terms:
        return escaped_text

    if text_color:
        style = (
            f"background-color: {bg_color}; "
            f"font-weight: {font_weight}; "
            f"color: {text_color};"
        )
    else:
        style = f"background-color: {bg_color}; font-weight: {font_weight};"

    pattern = re.compile(
        "|".join(re.escape(term) for term in normalized_terms),
        re.IGNORECASE,
    )
    return pattern.sub(
        lambda match: f'<span style="{style}">{match.group(0)}</span>',
        escaped_text,
    )
