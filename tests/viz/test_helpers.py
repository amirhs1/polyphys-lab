"""Tests of :mod:`polyphys.viz.helpers` on a study's space table.

The test draws the research code's TransFociCub gyration space table with
the helpers and checks the figure's properties; it runs only with the
maintainer's data.
"""
import importlib

import pytest

pytest.importorskip("matplotlib")

import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402

from polyphys.viz.helpers import color_handles, set_xticks  # noqa: E402


# On the research code's space table (tier C)


def _plot_state_points(ax, table, colors):  # pragma: no cover - tier C
    """One line per state point of a space table, ``gyrTMon-mean`` against
    ``time``, in the given colors; returns the labels, the rounded crowder
    volume fractions."""
    labels = []
    for (phi, rows), color in zip(table.groupby("phi_bulk_c_round"), colors):
        ax.plot(rows["time"], rows["gyrTMon-mean"], color=color)
        labels.append(f"{phi:g}")
    return labels


@pytest.mark.private_data
def test_helpers_draw_the_research_space_table(  # pragma: no cover
        ax, private_data_dir):
    """A figure of the research code's TransFociCub gyration space table has
    one line per state point, one legend handle per line in its color from
    ``color_handles``, and x ticks from ``set_xticks`` whose first and last
    frame the time axis. A property check: there is no research figure to
    compare with."""
    from polyphys.analyze.pipeline import space_tseries_from_spec

    spec = importlib.import_module("polyphys_lab.trans_foci_cub.spec").SPEC
    parent = private_data_dir / "TransFociCub" / "analysis"
    folders = sorted(parent.glob("*-bug-ensAvg"))
    if len(folders) != 1:
        pytest.skip(f"no single *-bug-ensAvg folder under {parent}")
    table = space_tseries_from_spec(folders[0], spec, "gyrTMon")
    n_states = table["ensemble_long"].nunique()
    colors = [tuple(color) for color in matplotlib.colormaps["viridis"](
        np.linspace(0.0, 1.0, n_states))]
    t_max = float(table["time"].max())

    labels = _plot_state_points(ax, table, colors)
    handles = color_handles(labels, colors)
    ticks = set_xticks(ax, 0.0, t_max, t_max / 5)

    assert len(ax.lines) == n_states == len(handles)
    assert [to_rgba(handle.get_facecolor()) for handle in handles] == [
        to_rgba(line.get_color()) for line in ax.lines]
    assert ticks[0] <= table["time"].min() and ticks[-1] >= t_max
    assert ax.get_xlim()[0] <= 0.0 and ax.get_xlim()[1] >= t_max
