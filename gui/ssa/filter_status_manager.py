"""Utilities to format and apply filter status messages in a single place."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilterStatusPayload:
    filtered_total: int
    original_total: int
    search_text: str = ""
    suffix: str = ""


class FilterStatusManager:
    """Centralizes status formatting and label update behavior."""

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
    def build_count_status_text(cls, filtered_total: int, original_total: int) -> str:
        return cls.format_status(
            cls.build_count_content(
                filtered_total=filtered_total,
                original_total=original_total,
            )
        )

    @classmethod
    def apply(
        cls,
        payload: FilterStatusPayload,
        filtered_status_label,
        status_label,
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

        shares_single_status_label = (
            filtered_status_label is None
            or status_label is None
            or filtered_status_label is status_label
        )

        if shares_single_status_label:
            merged_content = (
                f"{count_content}. {notice_content}" if notice_content else count_content
            )
            merged_status_text = cls.format_status(merged_content)
            target_label = status_label if status_label is not None else filtered_status_label
            if target_label is not None:
                target_label.setText(merged_status_text)
            return merged_status_text, merged_status_text

        if filtered_status_label is not None:
            filtered_status_label.setText(count_status_text)
        if status_label is not None:
            status_label.setText(notice_status_text)
        return count_status_text, notice_status_text
