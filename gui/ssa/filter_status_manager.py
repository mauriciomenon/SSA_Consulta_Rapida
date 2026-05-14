"""Utilities to format filter status messages in a single place."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilterStatusPayload:
    filtered_total: int
    original_total: int
    search_text: str = ""
    suffix: str = ""


class FilterStatusManager:
    """Centralizes status formatting behavior."""

    @staticmethod
    def format_status(content: str = "") -> str:
        raw = str(content or "").strip()
        if not raw:
            return "Status: Pronto."
        return f"Status: {raw}"

    @staticmethod
    def build_count_content(filtered_total: int, original_total: int) -> str:
        return f"{int(filtered_total)} de {int(original_total)} SSAs"

    @staticmethod
    def build_notice_content(search_text: str = "", suffix: str = "") -> str:
        search_value = str(search_text or "").strip()
        suffix_text = str(suffix or "").strip()
        if search_value and suffix_text:
            return f"Busca para '{search_value}'. {suffix_text}"
        if search_value:
            return f"Busca para '{search_value}'"
        if suffix_text:
            return suffix_text
        return ""

    @classmethod
    def build_status_texts(
        cls,
        payload: FilterStatusPayload,
        *,
        split_labels: bool,
    ) -> tuple[str, str]:
        count_content = cls.build_count_content(
            filtered_total=payload.filtered_total,
            original_total=payload.original_total,
        )
        notice_content = cls.build_notice_content(
            search_text=payload.search_text,
            suffix=payload.suffix,
        )

        count_status_text = cls.format_status(count_content)
        notice_status_text = (
            cls.format_status(notice_content)
            if notice_content
            else cls.format_status("")
        )

        if not split_labels:
            merged_content = (
                f"{count_content}. {notice_content}"
                if notice_content
                else count_content
            )
            merged_status_text = cls.format_status(merged_content)
            return merged_status_text, merged_status_text

        return count_status_text, notice_status_text
