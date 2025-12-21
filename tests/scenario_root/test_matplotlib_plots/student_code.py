import matplotlib.pyplot as plt
import numpy as np
from plot_serializer.matplotlib.serializer import MatplotlibSerializer


def create_line_plot():
    """Create a simple line plot with proper labels and title."""
    fig, ax = plt.subplots()
    x = np.linspace(0, 2 * np.pi, 100)
    y = np.sin(x)
    ax.plot(x, y, label="sin(x)", color="blue", linewidth=2)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("Sine Wave")
    ax.legend()
    ax.grid(True)
    return MatplotlibSerializer(fig)


def create_scatter_plot():
    """Create a scatter plot with random data."""
    fig, ax = plt.subplots()
    np.random.seed(42)
    x = np.random.randn(50)
    y = 2 * x + np.random.randn(50) * 0.5
    ax.scatter(x, y, c="red", alpha=0.6, s=50)
    ax.set_xlabel("X values")
    ax.set_ylabel("Y values")
    ax.set_title("Scatter Plot")
    return MatplotlibSerializer(fig)


def create_bar_chart():
    """Create a bar chart."""
    fig, ax = plt.subplots()
    categories = ["A", "B", "C", "D"]
    values = [23, 45, 56, 78]
    ax.bar(categories, values, color=["red", "green", "blue", "yellow"])
    ax.set_xlabel("Category")
    ax.set_ylabel("Value")
    ax.set_title("Bar Chart")
    return MatplotlibSerializer(fig)


def create_multi_subplot():
    """Create a figure with multiple subplots."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # First subplot: line plot
    x = np.linspace(0, 10, 100)
    ax1.plot(x, np.exp(-x / 10) * np.cos(x))
    ax1.set_title("Damped Cosine")
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    
    # Second subplot: histogram
    data = np.random.normal(0, 1, 1000)
    ax2.hist(data, bins=30, color="green", alpha=0.7)
    ax2.set_title("Normal Distribution")
    ax2.set_xlabel("Value")
    ax2.set_ylabel("Frequency")
    
    fig.tight_layout()
    return MatplotlibSerializer(fig)
