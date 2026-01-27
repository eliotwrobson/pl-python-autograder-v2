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
