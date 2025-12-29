import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend
import numpy as np
import pytest
from matplotcheck.base import PlotTester
from matplotlib.figure import Figure

from pytest_prairielearn_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="line_plot_basic", points=2)
def test_line_plot_basic(sandbox: StudentFixture) -> None:
    """Test that the line plot is created correctly."""
    # Get the serialized figure from student code (auto-deserialized)
    plot = sandbox.query_function("create_line_plot")
    assert len(plot.axes) == 1

    ax = plot.axes[0]
    pt = PlotTester(ax)

    # Check axis labels and title using PlotTester assertions
    pt.assert_axis_label_contains(axis="x", strings_expected=["x"])
    pt.assert_axis_label_contains(axis="y", strings_expected=["y"])
    pt.assert_title_contains(["Sine Wave"])


@pytest.mark.grading_data(name="line_plot_matplotcheck", points=2)
def test_line_plot_with_matplotcheck(sandbox: StudentFixture) -> None:
    """Test line plot using matplotcheck."""
    plot = sandbox.query_function("create_line_plot")

    # Use PlotTester to check plot properties
    pt = PlotTester(plot.axes[0])

    # Check that there is exactly one line
    assert len(pt.ax.lines) == 1

    # Check the line properties using PlotTester assertions
    line = pt.ax.lines[0]
    assert line.get_label() == "sin(x)"
    # Color is returned as hex after serialization
    assert line.get_color() in ["blue", "#0000FF", "#0000ffff"]
    assert line.get_linewidth() == 2


@pytest.mark.grading_data(name="scatter_plot", points=2)
def test_scatter_plot(sandbox: StudentFixture) -> None:
    """Test scatter plot creation."""
    plot = sandbox.query_function("create_scatter_plot")

    assert isinstance(plot, Figure)
    assert len(plot.axes) == 1

    ax = plot.axes[0]
    pt = PlotTester(ax)

    # Check plot type and labels using PlotTester assertions
    pt.assert_plot_type("scatter")
    pt.assert_axis_label_contains(axis="x", strings_expected=["X values"])
    pt.assert_axis_label_contains(axis="y", strings_expected=["Y values"])
    pt.assert_title_contains(["Scatter Plot"])

    # Check scatter plot exists
    assert len(pt.ax.collections) > 0


@pytest.mark.grading_data(name="bar_chart", points=2)
def test_bar_chart(sandbox: StudentFixture) -> None:
    """Test bar chart creation."""
    plot = sandbox.query_function("create_bar_chart")

    assert isinstance(plot, Figure)
    ax = plot.axes[0]
    pt = PlotTester(ax)

    # Check plot type using PlotTester
    pt.assert_plot_type("bar")

    # Check labels and title
    pt.assert_axis_label_contains(axis="x", strings_expected=["Category"])
    pt.assert_axis_label_contains(axis="y", strings_expected=["Value"])
    pt.assert_title_contains(["Bar Chart"])

    # Check for bar patches
    bars = list(ax.patches)
    assert len(bars) == 4

    # Check bar heights
    bar_heights = [bar.get_height() for bar in bars]
    expected_heights = [23, 45, 56, 78]
    np.testing.assert_array_almost_equal(bar_heights, expected_heights)


@pytest.mark.grading_data(name="multi_subplot", points=2)
def test_multi_subplot(sandbox: StudentFixture) -> None:
    """Test figure with multiple subplots."""
    plot = sandbox.query_function("create_multi_subplot")

    assert isinstance(plot, Figure)

    # Should have exactly 2 subplots
    assert len(plot.axes) == 2

    ax1, ax2 = plot.axes
    pt1 = PlotTester(ax1)
    pt2 = PlotTester(ax2)

    # Check first subplot (line plot)
    pt1.assert_title_contains(["Damped Cosine"])
    pt1.assert_axis_label_contains(axis="x", strings_expected=["x"])
    pt1.assert_axis_label_contains(axis="y", strings_expected=["y"])
    assert len(ax1.lines) == 1

    # Check second subplot (histogram)
    pt2.assert_title_contains(["Normal Distribution"])
    pt2.assert_axis_label_contains(axis="x", strings_expected=["Value"])
    pt2.assert_axis_label_contains(axis="y", strings_expected=["Frequency"])

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

    # Check that y data is approximately sin(x) using PlotTester
    expected_y = np.sin(xdata)
    np.testing.assert_array_almost_equal(ydata, expected_y, decimal=10)
