"""Configuration dataclass for pytest-prairielearn-grader."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigObject:
    """
    Configuration object for the autograder sandbox environment.

    This dataclass provides type-safe configuration for all autograder settings
    that can be set using the data["params"] dictionary or module-level variables.
    When provided to a test, this configuration takes precedence over all other
    configuration sources (data.json params, module-level variables, etc.).

    This class is immutable (frozen) and uses slots for memory efficiency.
    All constructor arguments must be passed as keyword arguments.

    Example usage:
        ```python
        from pytest_prairielearn_grader import ConfigObject

        # Define configuration at module level - plugin will automatically detect it
        autograder_config = ConfigObject(
            sandbox_timeout=2.0,
            import_whitelist=["numpy", "math"],
            builtin_whitelist=["len", "range", "sum"],
            starting_vars={"coefficient": 10}
        )

        def test_student_code(sandbox):
            result = sandbox.query_function("student_func")
            assert result.status == "success"
        ```
    """

    sandbox_timeout: float = 1.0
    """Timeout in seconds for sandbox initialization and operations.

    Must be a positive number. Default is 1.0 second.
    This timeout applies to both sandbox initialization and individual student code operations.
    """

    import_whitelist: list[str] | None = None
    """List of allowed Python modules that student code can import.

    If set, only these modules can be imported (whitelist mode).
    If None, all modules are allowed except those in import_blacklist.
    Can be combined with import_blacklist - blacklist is checked first, then whitelist.

    Example: ["numpy", "math", "pandas"]
    """

    import_blacklist: list[str] | None = None
    """List of Python modules that student code is prohibited from importing.

    Modules in the blacklist are always blocked, even if in the whitelist.
    Can be combined with import_whitelist for fine-grained control.
    Default blocks dangerous system operations: ["os", "sys", "subprocess", "pathlib", "shutil"].

    Example: ["requests", "socket"]
    """

    builtin_whitelist: list[str] | None = None
    """List of allowed Python builtin functions that student code can use.

    If set, only these builtins are accessible in student code (whitelist mode).
    If None, all builtins are available.

    Example: ["len", "range", "sum", "print"]
    """

    names_for_user: list[str] | None = None
    """List of variable names to inject into student sandbox.

    Only variables listed here will be injected into student code.
    Values are taken from starting_vars or from setup_code execution.
    This is a simplified version for ConfigObject - just provide variable names.

    Example: ["coefficient", "threshold", "data_array"]
    """

    student_code_pattern: str = "student_code*.py"
    """Glob pattern for finding student code files.

    Used by pytest_generate_tests to discover student code variants.
    Default is "student_code*.py".
    Must be a valid glob pattern.

    Example: "submission*.py"
    """

    starting_vars: dict[str, Any] = field(default_factory=dict)
    """Additional variables to inject into the student sandbox namespace.

    This is a dictionary of variable names to values.
    Variables must also be listed in names_for_user to be injected into student code.
    This allows ConfigObject to override values from data.json params.

    Example: {"constant": 42, "data_array": [1, 2, 3]}
    """

    workspace_mode: bool = False
    """Enable workspace grading mode.

    When True, the autograder uses the workspace_sandbox fixture instead of the
    regular sandbox.  In workspace mode the student's submission is treated as a
    multi-file Python project rooted at workspace_student_dir rather than a single
    script.  Tests query functions and variables using dotted module paths such as
    ``"models.classifier.predict"`` instead of bare function names.

    Default is False (normal single-file mode).
    """

    workspace_student_dir: str | None = None
    """Path to the student's workspace directory.

    Interpreted according to the following rules:
    - If an absolute path (starts with '/'): used as-is.
    - If a relative path or None: resolved relative to the directory that contains
      the test module (the same directory where data.json lives).  When None, the
      fixture looks for a sub-directory named ``"student"`` next to the test file,
      which mirrors the ``/grade/student/`` directory PrairieLearn provides during
      autograding.

    For PrairieLearn deployment, set this to ``"/grade/student"`` (or leave None and
    ensure a ``student/`` directory exists next to your test file for local dev).

    Example: "/grade/student"
    """

    workspace_exec_entry: str | None = None
    """Optional entry-point file to execute at sandbox startup in workspace mode.

    When set, the file is executed (via ``exec``) inside the sandbox after
    ``sys.path`` has been set up and after ``setup_code.py`` has run.  This is
    useful for questions where a student's ``main.py`` sets up global state that
    tests depend on.

    The path is relative to workspace_student_dir.

    If None (default), no file is executed at startup; tests import modules
    on-demand using dotted paths.

    Example: "main.py"
    """

    notebook_cell_tag: str | None = None
    """Tag used to filter Jupyter notebook code cells for grading.

    When the student submission is a ``.ipynb`` notebook file, this tag controls
    which code cells are extracted and executed in the sandbox.

    - If ``None`` (default), **all** code cells in the notebook are included.
    - If set to a string (e.g. ``"#grade"``), only code cells whose first
      non-empty line starts with that string are included.  This mirrors the
      convention used by the built-in PrairieLearn Python autograder.

    To use this feature the ``student_code_pattern`` must match ``.ipynb``
    files (e.g. ``"student_code*.ipynb"``), and ``nbformat`` must be installed
    (``pip install pytest-prairielearn-grader[notebook]``).

    This field has no effect when the student submission is a plain ``.py`` file
    or when workspace mode is enabled.

    Example: "#grade"
    """

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Validate sandbox_timeout
        if self.sandbox_timeout <= 0:
            raise ValueError(f"sandbox_timeout must be positive, got {self.sandbox_timeout}")

        # Validate import_whitelist contains non-empty strings
        if self.import_whitelist is not None:
            if not isinstance(self.import_whitelist, list):
                raise TypeError(f"import_whitelist must be a list, got {type(self.import_whitelist).__name__}")
            if not self.import_whitelist:
                raise ValueError("import_whitelist cannot be empty (use None to allow all imports)")
            for module_name in self.import_whitelist:
                if not isinstance(module_name, str) or not module_name.strip():
                    raise ValueError(f"import_whitelist must contain non-empty strings, got: {module_name!r}")

        # Validate import_blacklist contains non-empty strings
        if self.import_blacklist is not None:
            if not isinstance(self.import_blacklist, list):
                raise TypeError(f"import_blacklist must be a list, got {type(self.import_blacklist).__name__}")
            for module_name in self.import_blacklist:
                if not isinstance(module_name, str) or not module_name.strip():
                    raise ValueError(f"import_blacklist must contain non-empty strings, got: {module_name!r}")

        # Validate builtin_whitelist contains non-empty strings
        if self.builtin_whitelist is not None:
            if not isinstance(self.builtin_whitelist, list):
                raise TypeError(f"builtin_whitelist must be a list, got {type(self.builtin_whitelist).__name__}")
            if not self.builtin_whitelist:
                raise ValueError("builtin_whitelist cannot be empty (use None to allow all builtins)")
            for builtin_name in self.builtin_whitelist:
                if not isinstance(builtin_name, str) or not builtin_name.strip():
                    raise ValueError(f"builtin_whitelist must contain non-empty strings, got: {builtin_name!r}")

        # Validate names_for_user structure
        if self.names_for_user is not None:
            if not isinstance(self.names_for_user, list):
                raise TypeError(f"names_for_user must be a list, got {type(self.names_for_user).__name__}")
            if not self.names_for_user:
                raise ValueError("names_for_user cannot be empty (use None to inject no variables)")
            for name in self.names_for_user:
                if not isinstance(name, str) or not name.strip():
                    raise ValueError(f"names_for_user must contain non-empty strings, got: {name!r}")

        # Validate student_code_pattern is non-empty
        if not isinstance(self.student_code_pattern, str) or not self.student_code_pattern.strip():
            raise ValueError(f"student_code_pattern must be a non-empty string, got: {self.student_code_pattern!r}")

        # Validate starting_vars is a dict
        if not isinstance(self.starting_vars, dict):
            raise TypeError(f"starting_vars must be a dict, got {type(self.starting_vars).__name__}")

        # Validate workspace fields
        if not isinstance(self.workspace_mode, bool):
            raise TypeError(f"workspace_mode must be a bool, got {type(self.workspace_mode).__name__}")

        if self.workspace_student_dir is not None:
            if not isinstance(self.workspace_student_dir, str) or not self.workspace_student_dir.strip():
                raise ValueError(f"workspace_student_dir must be a non-empty string, got: {self.workspace_student_dir!r}")
            if not self.workspace_mode:
                raise ValueError(
                    "workspace_student_dir requires workspace_mode=True. "
                    "Set workspace_mode=True or remove workspace_student_dir."
                )

        if self.workspace_exec_entry is not None:
            if not isinstance(self.workspace_exec_entry, str) or not self.workspace_exec_entry.strip():
                raise ValueError(f"workspace_exec_entry must be a non-empty string, got: {self.workspace_exec_entry!r}")
            if not self.workspace_mode:
                raise ValueError(
                    "workspace_exec_entry requires workspace_mode=True. "
                    "Set workspace_mode=True or remove workspace_exec_entry."
                )

        if self.notebook_cell_tag is not None:
            if not isinstance(self.notebook_cell_tag, str) or not self.notebook_cell_tag.strip():
                raise ValueError(f"notebook_cell_tag must be a non-empty string, got: {self.notebook_cell_tag!r}")
            if self.workspace_mode:
                raise ValueError(
                    "notebook_cell_tag is not supported in workspace mode. "
                    "Set workspace_mode=False or remove notebook_cell_tag."
                )

        # Validate cross-mode conflicts
        if self.workspace_mode and self.student_code_pattern != "student_code*.py":
            raise ValueError(
                "student_code_pattern is not applicable in workspace mode "
                "(workspace_mode=True). Remove student_code_pattern or set workspace_mode=False."
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the ConfigObject to a dictionary format compatible with data["params"].

        Returns:
            Dictionary representation of the configuration.
        """
        result: dict[str, Any] = {}

        if self.import_whitelist is not None:
            result["import_whitelist"] = self.import_whitelist
        if self.import_blacklist is not None:
            result["import_blacklist"] = self.import_blacklist
        if self.builtin_whitelist is not None:
            result["builtin_whitelist"] = self.builtin_whitelist
        if self.names_for_user is not None:
            result["names_for_user"] = self.names_for_user

        return result
