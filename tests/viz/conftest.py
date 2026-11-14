"""
Fixtures for the lab's tests of :mod:`polyphys.viz` figures.

Every figure is drawn with the Agg backend, which needs no display, and
closed by the fixture that made it.
"""
from typing import Any, Iterator

import pytest


@pytest.fixture
def figure() -> Iterator[Any]:
    """An empty Agg figure, closed after the test."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    yield fig
    plt.close(fig)


@pytest.fixture
def ax(figure: Any) -> Any:
    """One empty axes on the test's figure."""
    return figure.add_subplot()
