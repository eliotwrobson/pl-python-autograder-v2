import numpy as np
import numpy.linalg as la


def solve_ratings(members, sale_metadata):
    sale_metadata = [
        {"hours": [("Bob", 50), ("Greg", 45), ("Susan", 25)], "units_sold": 160},
        {"hours": [("Greg", 50), ("Bob", 25), ("Susan", 70)], "units_sold": 180},
        {"hours": [("Bob", 35), ("Susan", 45), ("Greg", 25)], "units_sold": 150},
    ]

    members = ["Bob", "Susan", "Greg"]
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
