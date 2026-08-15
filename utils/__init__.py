"""utils package initializer.

Re-exports setup_project_structure after accidental removal so that
`from utils import setup_project_structure` works again.
"""

from . import setup_project_structure  # noqa: F401

