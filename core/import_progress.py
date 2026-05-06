from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import cast

_NUMERIC_TEXT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


@dataclass
class ImportProgressSummary:
    total_candidates: int = 0
    processed_files: int = 0
    errors: list[object] = field(default_factory=list)

    @staticmethod
    def count(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            if not math.isfinite(value):
                return 0
            return max(int(value), 0)
        if isinstance(value, str):
            text = value.strip()
            if not _NUMERIC_TEXT_RE.fullmatch(text):
                return 0
            number = float(text)
            if not math.isfinite(number):
                return 0
            return max(int(number), 0)
        return 0

    def capture(self, event_type: str, data: dict[str, object]) -> None:
        if not isinstance(data, dict):
            return
        if event_type == "start":
            self.total_candidates = self.count(data.get("total"))
        elif event_type == "file_error":
            self.errors.append(
                str(data.get("error") or data.get("filename") or "erro")
            )
        elif event_type == "finish":
            self.total_candidates = self.count(
                data.get("total", self.total_candidates)
            )
            self.processed_files = self.count(data.get("processed"))
            reported_errors = data.get("errors")
            if isinstance(reported_errors, list):
                self.errors = cast(list[object], reported_errors)
