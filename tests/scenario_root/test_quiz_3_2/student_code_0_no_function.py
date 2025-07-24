import numpy.linalg as la

index = -1
p_norm = float("inf")

for i, r in enumerate(stock_returns):
    pp = la.norm(r - market_trend, ord=p) / la.norm(r, ord=p)
    if pp < p_norm:
        index = i
        p_norm = la.norm(r, ord=p)
