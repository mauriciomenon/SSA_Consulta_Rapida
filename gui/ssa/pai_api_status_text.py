"""Status text helpers for PAI API GUI flows."""

from __future__ import annotations

PAI_API_STATUS_DETAIL_MAX_LENGTH = 88


def trim_pai_api_status_detail(
    message: object,
    *,
    max_length: int = PAI_API_STATUS_DETAIL_MAX_LENGTH,
) -> str:
    text = " ".join(str(message or "").split())
    if not text:
        return "erro sem detalhe"
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."
