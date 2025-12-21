import matplotlib.pyplot as plt
import pytest
import matplotcheck as mpc
from matplotcheck.base import PlotTester

from pytest_pl_grader.fixture import StudentFixture


@pytest.mark.grading_data(name="simple_plot_test", points=2)
def test_simple_plot(sandbox: StudentFixture) -> None:
    """Test a simple plot using both basic assertions and matplotcheck."""
    # Get the serialized figure from student code
    plot = sandbox.query_function("create_simple_plot")
    
    # Basic assertions
    assert isinstance(plot, plt.Figure)
    assert len(plot.axes) == 1
    
    ax = plot.axes[0]
    assert ax.get_xlabel() == "X"
    assert ax.get_ylabel() == "Y"
    assert ax.get_title() == "Simple Plot"
    
    # Use matplotcheck PlotTester
    pt = PlotTester(ax)
    assert len(pt.axis.lines) == 1
