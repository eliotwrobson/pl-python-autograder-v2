import typing as t
from copy import deepcopy

from RestrictedPython import CompileResult, compile_restricted_exec
from RestrictedPython.Guards import safe_globals

from .restricted_import import _safe_import


class RestrictedExecutor:
    compile_result: CompileResult
    defined_symbols: t.Dict[str, t.Any]

    def __init__(self, code: str) -> None:
        self.compile_result = compile_restricted_exec(code)

    def execute(self) -> None:
        global_dict = deepcopy(safe_globals)

        global_dict["__builtins__"].update({"__import__": _safe_import(__import__, [])})

        exec(self.compile_result.code, global_dict)

        for key in safe_globals:
            del global_dict[key]

        self.defined_symbols = global_dict

    def get_defined_symbols(self) -> t.Dict[str, t.Any]:
        return self.defined_symbols
