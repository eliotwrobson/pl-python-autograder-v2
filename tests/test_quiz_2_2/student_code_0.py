import math

largest_fp = 2**7 * (1 - 2 ** (-4))
machine_epsilon = 2 ** (-3)

start_exp = math.log(start, 2)
end_exp = math.log(end, 2)

start_frac = start / 2**start_exp
end_frac = end / 2**end_exp

fp_lst = []

for e in range(start_exp, end_exp + 1):
    for i in range(8):
        if e == start_exp and 1 + float(i) / 8 < start_frac:
            continue
        if e == end_exp and 1 + float(i) / 8 > end_frac:
            continue
        fp_lst.append((1 + float(i) / 8) * 2**e)
