"""Import pipeline exception types."""

from __future__ import annotations


class ImporterError(Exception):
    """Base exception for import pipeline errors."""


class CacheError(ImporterError):
    """Cache system error."""


class ExtractionError(ImporterError):
    """Data extraction error for a source file."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class DatabaseError(ImporterError):
    """Database operation error."""


class ImportMetricsContractError(DatabaseError):
    """Successful database write omitted mandatory import metrics."""

    def __init__(self, message: str, *, record_count: int):
        super().__init__(message)
        self.record_count = int(record_count)


class DatabaseConnectionError(DatabaseError):
    """Database connection error."""


class DatabaseCorruptionError(DatabaseError):
    """Database corruption error."""


class DatabaseSchemaError(DatabaseError):
    """Database schema error."""


class DatabaseSpaceError(DatabaseError):
    """Insufficient database storage error."""


class DataValidationError(ImporterError):
    """Data validation error before insertion."""
