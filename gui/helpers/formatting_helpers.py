# gui/helpers/formatting_helpers.py
# Pure formatting helper functions

import re
import html


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




def highlight_text(
    text: str,
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
        if text_color:
            style = (
                f"background-color: {bg_color}; "
                f"font-weight: {font_weight}; "
                f"color: {text_color};"
            )
        else:
            style = f"background-color: {bg_color}; font-weight: {font_weight};"
        text_escaped = pattern.sub(
            lambda m: f'<span style="{style}">{m.group()}</span>',
            text_escaped,
        )

    return text_escaped
