import numpy.linalg as la


def most_consistent_stock(stock_returns, market_trend, p):
    index = p_norm = -1
    min_val = float("inf")

    for i, r in enumerate(stock_returns):
        pp = la.norm(r - market_trend, ord=p) / la.norm(r, ord=p)
        if pp < min_val:
            index = i
            min_val = pp
            p_norm = la.norm(r, ord=p)

    return index, p_norm
