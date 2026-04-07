try:
    from importlib.metadata import version

    __version__ = version("pytest-prairielearn-grader")
except Exception:
    __version__ = "0.0.0"

from .assertions import assert_approx_equal
from .assertions import assert_equal
from .assertions import assert_false
from .assertions import assert_fn_approx_equal
from .assertions import assert_fn_equal
from .assertions import assert_true
from .config import ConfigObject
from .fixture import WorkspaceFixture

__all__ = [
    "ConfigObject",
    "WorkspaceFixture",
    "__version__",
    "assert_approx_equal",
    "assert_equal",
    "assert_false",
    "assert_fn_approx_equal",
    "assert_fn_equal",
    "assert_true",
]
