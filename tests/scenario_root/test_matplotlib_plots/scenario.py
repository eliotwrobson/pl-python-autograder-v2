import matplotlib.pyplot as plt
import numpy as np
import pytest
import matplotcheck as mpc
from matplotcheck.base import PlotTester

from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="line_plot_basic", points=2)
def test_line_plot_basic(sandbox: StudentFixture) -> None:
    """Test that the line plot is created correctly."""
    # Get the serialized figure from student code
    plot = sandbox.query_function("create_line_plot")
    
    # Basic assertions - check it's a matplotlib figure
    assert isinstance(plot, plt.Figure)
    assert len(plot.axes) == 1
    
    ax = plot.axes[0]
    assert ax.get_xlabel() == "x"
    assert ax.get_ylabel() == "y"
    assert ax.get_title() == "Sine Wave"


@pytest.mark.grading_data(name="line_plot_matplotcheck", points=2)
def test_line_plot_with_matplotcheck(sandbox: StudentFixture) -> None:
    """Test line plot using matplotcheck."""
    plot = sandbox.query_function("create_line_plot")
    
    # Use PlotTester to check plot properties
    pt = PlotTester(plot.axes[0])
    
    # Check that there is exactly one line
    assert len(pt.axis.lines) == 1
    
    # Check the line properties
    line = pt.axis.lines[0]
    assert line.get_label() == "sin(x)"
    assert line.get_color() == "blue"
    assert line.get_linewidth() == 2
    
    # Check that grid is enabled
    assert pt.axis.get_xgridlines()[0].get_visible() or pt.axis.xaxis.get_gridlines()[0].get_visible()


@pytest.mark.grading_data(name="scatter_plot", points=2)
def test_scatter_plot(sandbox: StudentFixture) -> None:
    """Test scatter plot creation."""
    plot = sandbox.query_function("create_scatter_plot")
    
    assert isinstance(plot, plt.Figure)
    assert len(plot.axes) == 1
    
    ax = plot.axes[0]
    pt = PlotTester(ax)
    
    # Check scatter plot exists
    assert len(pt.axis.collections) > 0
    
    # Check labels
    assert ax.get_xlabel() == "X values"
    assert ax.get_ylabel() == "Y values"
    assert ax.get_title() == "Scatter Plot"
    
    # Check scatter properties
    scatter = pt.axis.collections[0]
    # Should have 50 points
    assert len(scatter.get_offsets()) == 50


@pytest.mark.grading_data(name="bar_chart", points=2)
def test_bar_chart(sandbox: StudentFixture) -> None:
    """Test bar chart creation."""
    plot = sandbox.query_function("create_bar_chart")
    
    assert isinstance(plot, plt.Figure)
    ax = plot.axes[0]
    pt = PlotTester(ax)
    
    # Check for bar patches
    bars = [patch for patch in ax.patches]
    assert len(bars) == 4
    
    # Check labels
    assert ax.get_xlabel() == "Category"
    assert ax.get_ylabel() == "Value"
    assert ax.get_title() == "Bar Chart"
    
    # Check bar heights
    bar_heights = [bar.get_height() for bar in bars]
    expected_heights = [23, 45, 56, 78]
    np.testing.assert_array_almost_equal(bar_heights, expected_heights)


@pytest.mark.grading_data(name="multi_subplot", points=2)
def test_multi_subplot(sandbox: StudentFixture) -> None:
    """Test figure with multiple subplots."""
    plot = sandbox.query_function("create_multi_subplot")
    
    assert isinstance(plot, plt.Figure)
    
    # Should have exactly 2 subplots
    assert len(plot.axes) == 2
    
    ax1, ax2 = plot.axes
    
    # Check first subplot (line plot)
    assert ax1.get_title() == "Damped Cosine"
    assert ax1.get_xlabel() == "x"
    assert ax1.get_ylabel() == "y"
    assert len(ax1.lines) == 1
    
    # Check second subplot (histogram)
    assert ax2.get_title() == "Normal Distribution"
    assert ax2.get_xlabel() == "Value"
    assert ax2.get_ylabel() == "Frequency"
    
    # Check histogram patches exist
    assert len(ax2.patches) == 30  # 30 bins


@pytest.mark.grading_data(name="line_data_accuracy", points=2)
def test_line_plot_data_accuracy(sandbox: StudentFixture) -> None:
    """Test that the line plot contains correct data points."""
    plot = sandbox.query_function("create_line_plot")
    
    ax = plot.axes[0]
    line = ax.lines[0]
    
    # Get the line data
    xdata = line.get_xdata()
    ydata = line.get_ydata()
    
    # Check that x ranges from 0 to 2π
    assert np.isclose(xdata[0], 0, atol=0.01)
    assert np.isclose(xdata[-1], 2 * np.pi, atol=0.01)
    
    # Check that y data is approximately sin(x)
    expected_y = np.sin(xdata)
    np.testing.assert_array_almost_equal(ydata, expected_y, decimal=10)
