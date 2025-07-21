def not_allowed(*args, **kwargs):
    raise RuntimeError("Calling sympy.series is not allowed in this question. You can still use sympy to compute derivatives")


import sympy as sp

sp.series = not_allowed
