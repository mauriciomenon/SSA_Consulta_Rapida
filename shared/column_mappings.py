"""Forwarder to break dependency cycle between extracao and core."""

from core.config_manager import load_column_mappings_integrity as _impl

def load_column_mappings_integrity():
    return _impl()
