from sympy import series
from sympy import tan
from sympy.abc import x

f = tan(x)
series(f, x, 2, 6, "+")
