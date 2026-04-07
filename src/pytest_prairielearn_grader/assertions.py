"""Student-friendly assertion helpers for the PrairieLearn autograder.

These functions produce clean, readable failure messages designed for students
who may not be comfortable reading Python tracebacks.  Combine these with
``@pytest.mark.output(level="friendly")`` to suppress all traceback noise and
show *only* the human-readable message.

Typical usage::

    from pytest_prairielearn_grader.assertions import assert_equal, assert_fn_equal

    @pytest.mark.output(level="friendly")
    @pytest.mark.grading_data(name="Test addition", points=5)
    def test_add(sandbox):
        assert_fn_equal(sandbox, "add", args=(2, 3), expected=5)
"""

from __future__ import annotations

import os
from typing import Any

from .fixture import _SandboxBase


def _format_value(value: Any, *, max_len: int = 200) -> str:
    """Return a repr of *value*, truncated for readability."""
    text = repr(value)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _format_call(func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any] | None) -> str:
    """Format ``func_name(args, kwargs)`` for display."""
    parts: list[str] = [_format_value(a, max_len=60) for a in args]
    if kwargs:
        parts.extend(f"{k}={_format_value(v, max_len=60)}" for k, v in kwargs.items())
    return f"{func_name}({', '.join(parts)})"


def _build_failure_lines(
    *,
    expected: Any,
    actual: Any,
    description: str | None = None,
    msg: str | None = None,
) -> str:
    """Build the multi-line student-facing failure message."""
    lines: list[str] = []
    if description:
        lines.append(f"Checking: {description}")
    lines.append(f"Expected output: {_format_value(expected)}")
    lines.append(f"Your code output: {_format_value(actual)}")
    if msg:
        lines.append(msg)
    else:
        lines.append("The expected and actual output do not match.")
    return os.linesep.join(lines)


# ---------------------------------------------------------------------------
# Standalone assertions (work with any pre-computed values)
# ---------------------------------------------------------------------------


def assert_equal(
    actual: Any,
    expected: Any,
    *,
    msg: str | None = None,
    description: str | None = None,
) -> None:
    """Assert ``actual == expected`` with a student-friendly failure message.

    Parameters
    ----------
    actual:
        The value produced by student code.
    expected:
        The correct / reference value.
    msg:
        Optional custom message appended on failure.  When *None* a default
        "The expected and actual output do not match." message is used.
    description:
        Optional label like ``"add(2, 3)"`` shown as the *Checking:* line.

    Raises
    ------
    AssertionError
        With a clean, multi-line message when the values differ.
    """
    if actual == expected:
        return
    raise AssertionError(_build_failure_lines(expected=expected, actual=actual, description=description, msg=msg))


def assert_approx_equal(
    actual: Any,
    expected: Any,
    *,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    msg: str | None = None,
    description: str | None = None,
) -> None:
    """Assert two numeric values are approximately equal.

    Uses the formula ``|actual - expected| <= atol + rtol * |expected|``.

    Parameters
    ----------
    actual:
        The numeric value produced by student code.
    expected:
        The correct / reference numeric value.
    rtol:
        Relative tolerance (default ``1e-5``).
    atol:
        Absolute tolerance (default ``1e-8``).
    msg:
        Optional custom failure message.
    description:
        Optional label for the *Checking:* line.

    Raises
    ------
    AssertionError
        When the values are not within tolerance.
    """
    try:
        diff = abs(actual - expected)
        within_tolerance = diff <= atol + rtol * abs(expected)
    except TypeError:
        within_tolerance = False

    if within_tolerance:
        return

    default_msg = f"The values are not close enough (rtol={rtol}, atol={atol})."
    raise AssertionError(
        _build_failure_lines(
            expected=expected,
            actual=actual,
            description=description,
            msg=msg or default_msg,
        )
    )


def assert_true(
    condition: Any,
    *,
    msg: str | None = None,
) -> None:
    """Assert that *condition* is truthy with a student-friendly message.

    Parameters
    ----------
    condition:
        Any value; the assertion passes when ``bool(condition)`` is ``True``.
    msg:
        Custom failure message.  Defaults to
        ``"Expected the condition to be true, but it was false."``.
    """
    if condition:
        return
    raise AssertionError(msg or "Expected the condition to be true, but it was false.")


def assert_false(
    condition: Any,
    *,
    msg: str | None = None,
) -> None:
    """Assert that *condition* is falsy with a student-friendly message.

    Parameters
    ----------
    condition:
        Any value; the assertion passes when ``bool(condition)`` is ``False``.
    msg:
        Custom failure message.  Defaults to
        ``"Expected the condition to be false, but it was true."``.
    """
    if not condition:
        return
    raise AssertionError(msg or "Expected the condition to be false, but it was true.")


# ---------------------------------------------------------------------------
# Sandbox-integrated assertions (call student function + compare result)
# ---------------------------------------------------------------------------


def assert_fn_equal(
    sandbox: _SandboxBase,
    func_name: str,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    expected: Any,
    msg: str | None = None,
    query_timeout: float = 1.0,
) -> Any:
    """Call a student function and assert its return value equals *expected*.

    This is a convenience wrapper that combines
    ``sandbox.query_function(...)`` with :func:`assert_equal` and
    automatically produces a message like::

        Checking: add(2, 3)
        Expected output: 5
        Your code output: 4
        The expected and actual output do not match.

    Parameters
    ----------
    sandbox:
        The sandbox fixture (``StudentFixture`` or ``WorkspaceFixture``).
    func_name:
        Name of the function to call in the student sandbox.
    args:
        Positional arguments forwarded to the student function.
    kwargs:
        Keyword arguments forwarded to the student function.
    expected:
        The correct / reference return value.
    msg:
        Optional custom failure message.
    query_timeout:
        Timeout in seconds for the function call (default ``1.0``).

    Returns
    -------
    The return value from the student function (useful for further checks).

    Raises
    ------
    AssertionError
        When the return value does not equal *expected*.
    RuntimeError / TimeoutError / NameError
        Propagated from ``sandbox.query_function`` on execution errors.
    """
    call_kwargs = kwargs or {}
    actual = sandbox.query_function(func_name, *args, query_timeout=query_timeout, **call_kwargs)
    description = _format_call(func_name, args, kwargs)
    assert_equal(actual, expected, msg=msg, description=description)
    return actual


def assert_fn_approx_equal(
    sandbox: _SandboxBase,
    func_name: str,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    expected: Any,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    msg: str | None = None,
    query_timeout: float = 1.0,
) -> Any:
    """Call a student function and assert its return value is approximately
    equal to *expected*.

    Behaves like :func:`assert_fn_equal` but uses :func:`assert_approx_equal`
    for the comparison.

    Returns
    -------
    The return value from the student function.
    """
    call_kwargs = kwargs or {}
    actual = sandbox.query_function(func_name, *args, query_timeout=query_timeout, **call_kwargs)
    description = _format_call(func_name, args, kwargs)
    assert_approx_equal(actual, expected, rtol=rtol, atol=atol, msg=msg, description=description)
    return actual
