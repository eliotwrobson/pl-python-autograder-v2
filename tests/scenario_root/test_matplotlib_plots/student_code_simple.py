import matplotlib.pyplot as plt
import numpy as np
from plot_serializer.matplotlib.serializer import MatplotlibSerializer


def create_simple_plot():
    """Create a very simple line plot."""
    fig, ax = plt.subplots()
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]
    ax.plot(x, y)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Simple Plot")
    return MatplotlibSerializer(fig)
