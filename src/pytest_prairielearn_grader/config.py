"""Configuration dataclass for pytest-prairielearn-grader."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from .utils import NamesForUserInfo


@dataclass
class ConfigObject:
    """
    Configuration object for the autograder sandbox environment.

    This dataclass provides type-safe configuration for all autograder settings
    that can be set using the data["params"] dictionary or module-level variables.
    When provided to a test, this configuration takes precedence over all other
    configuration sources (data.json params, module-level variables, etc.).

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

    Attributes:
        sandbox_timeout: Timeout in seconds for sandbox initialization and operations.
            Default is 1.0 second.

        import_whitelist: List of allowed Python modules that student code can import.
            If set, only these modules can be imported (whitelist mode).
            If None, all modules except those in import_blacklist can be imported.
            Example: ["numpy", "math", "pandas"]

        import_blacklist: List of Python modules that student code is prohibited from importing.
            Default blocks dangerous system operations: ["os", "sys", "subprocess", "pathlib", "shutil"].
            Only applies when import_whitelist is None (blacklist mode).

        builtin_whitelist: List of allowed Python builtin functions that student code can use.
            If set, only these builtins are accessible (whitelist mode).
            If None, all builtins are available.
            Example: ["len", "range", "sum", "print"]

        names_for_user: List of variable definitions to inject into student sandbox.
            Each item should be a dict with keys: "name", "type", "description".
            Values are taken from data["params"] and injected as global variables.
            Example: [{"name": "coefficient", "type": "float", "description": "The multiplier"}]

        student_code_pattern: Glob pattern for finding student code files.
            Default is "student_code*.py".
            Used by pytest_generate_tests to discover student code variants.
            Example: "submission*.py"

        starting_vars: Additional variables to inject into the student sandbox namespace.
            This is a dictionary of variable names to values that will be available
            in the student code's global scope.
            Example: {"constant": 42, "data_array": [1, 2, 3]}
    """

    sandbox_timeout: float = 1.0
    import_whitelist: list[str] | None = None
    import_blacklist: list[str] | None = None
    builtin_whitelist: list[str] | None = None
    names_for_user: list[NamesForUserInfo] | None = None
    student_code_pattern: str = "student_code*.py"
    starting_vars: dict[str, Any] = field(default_factory=dict)

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
