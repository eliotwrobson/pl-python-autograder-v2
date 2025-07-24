import numpy as np
import numpy.linalg as la


def solve_ratings(members, sale_metadata):
    sales = np.zeros(len(sale_metadata))
    theMatrix = np.zeros((len(members), len(sale_metadata)))
    for i in range(len(sale_metadata)):
        for j in range(len(sale_metadata[i]["hours"])):
            col = members.index(sale_metadata[i]["hours"][j][0])
            theMatrix[i][col] = sale_metadata[i]["hours"][j][1]
        sales[i] = sale_metadata[i]["units_sold"]
    ratings = la.solve(theMatrix, sales)
    highest_performing = np.max(ratings)
    lowest_performing = np.min(ratings)
    member_ratings = dict(zip(members, ratings))

    return member_ratings, highest_performing, lowest_performing
