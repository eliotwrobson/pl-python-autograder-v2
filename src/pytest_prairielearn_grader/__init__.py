try:
    from importlib.metadata import version

    __version__ = version("pytest-prairielearn-grader")
except Exception:
    __version__ = "0.0.0"

from .config import ConfigObject
from .fixture import WorkspaceFixture

__all__ = ["ConfigObject", "WorkspaceFixture", "__version__"]
