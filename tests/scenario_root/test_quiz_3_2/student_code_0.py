import numpy.linalg as la


def most_consistent_stock(stock_returns, market_trend, p):
    index = -1
    p_norm = float("inf")

    for i, r in enumerate(stock_returns):
        pp = la.norm(r - market_trend, ord=p) / la.norm(r, ord=p)
        if pp < p_norm:
            index = i
            p_norm = la.norm(r, ord=p)

    return index, p_norm
