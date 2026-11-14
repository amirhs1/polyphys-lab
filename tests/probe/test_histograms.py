"""Tests of :mod:`polyphys.probe.histograms` on real frames.

The tests bin the tier B and tier C frames of the studies' wholes
(``tests/probe/conftest.py``, "Real frames") with each study's own probe spec
and parser. Their expected values are conservation: every position of a real
frame falls inside the edges, so each frame's counts sum to the species'
particle number in the whole's name, and the run's counts to the number of
frames times it.
"""
import numpy as np
import pytest


pytest.importorskip("MDAnalysis")

from polyphys.probe import SpatialHistograms, histogram_edges  # noqa: E402

# The dump reader warns that the frames carry no time step; the tests
# measure per frame and give no dt.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")


# Real frames


@pytest.fixture
def real_histograms(study_spec, real_universe):
    """Factory: :meth:`SpatialHistograms.from_spec` run on a real dump with
    its topology, with the edges of the whole's parser in `group`."""

    def _run(whole, topology, trajectory, group):
        module = study_spec(whole.study)
        parser = module.SPEC.parser(f"{whole.whole}.ring", 'whole', group)
        universe = real_universe(topology, trajectory)
        return SpatialHistograms.from_spec(universe, module.PROBE,
                                           parser).run()

    return _run


@pytest.fixture
def directions():
    """The one-dimensional histograms of each geometry."""
    return {'cubic': ('r',), 'cylindrical': ('r', 'z', 'theta')}


def _counted(analysis, species, directions):
    """Per species and direction: the distinct per-frame sums, and the sum
    over the run."""
    return {
        f"{d}{s}": (np.unique(analysis.results[f"{d}HistT{s}"].sum(axis=1))
                    .tolist(), int(analysis.results[f"{d}Hist{s}"].sum()))
        for s in species for d in directions}


def test_real_window_histograms_conserve_every_species(
        real_window_whole, real_files, real_histograms, study_spec,
        directions):
    """Every position of a real ``all`` window falls inside the edges: each
    frame counts every particle of each species once, and the run counts it
    once per frame."""
    probe = study_spec(real_window_whole.study).PROBE
    files = real_files(real_window_whole)
    counts = real_window_whole.window_counts()

    analysis = real_histograms(real_window_whole, files.data, files.window,
                               'all')

    assert _counted(analysis, probe.histogram_species,
                    directions[probe.geometry]) == {
        f"{d}{s}": ([counts[s]], counts[s] * real_window_whole.n_window_frames)
        for s in probe.histogram_species
        for d in directions[probe.geometry]}


def test_real_polymer_histograms_conserve_every_species(
        real_polymer_whole, real_files, real_histograms, study_spec,
        directions):
    """Every position of a real polymer dump falls inside the edges of its
    whole: each frame counts every particle of each species once, and the
    crowders, absent from the dump, not at all."""
    probe = study_spec(real_polymer_whole.study).PROBE
    files = real_files(real_polymer_whole)
    counts = real_polymer_whole.polymer_counts()

    analysis = real_histograms(real_polymer_whole, files.topology,
                               files.polymer, real_polymer_whole.group)

    assert _counted(analysis, probe.histogram_species,
                    directions[probe.geometry]) == {
        f"{d}{s}": ([counts[s]], counts[s] * 50)
        for s in probe.histogram_species
        for d in directions[probe.geometry]}


def test_real_window_histograms_have_one_int64_row_per_frame_and_bin(
        real_window_whole, real_files, real_histograms, study_spec,
        directions):
    """Each per-frame histogram of a real window is int64 with one row per
    frame and one column per bin of the whole's edges."""
    module = study_spec(real_window_whole.study)
    probe = module.PROBE
    files = real_files(real_window_whole)
    edges = histogram_edges(probe, module.SPEC.parser(
        f"{real_window_whole.whole}.ring", 'whole', 'all'))

    analysis = real_histograms(real_window_whole, files.data, files.window,
                               'all')

    assert {f"{d}{s}": (analysis.results[f"{d}HistT{s}"].dtype,
                        analysis.results[f"{d}HistT{s}"].shape)
            for s in probe.histogram_species
            for d in directions[probe.geometry]} == {
        f"{d}{s}": (np.dtype(np.int64),
                    (real_window_whole.n_window_frames, edges[d].size - 1))
        for s in probe.histogram_species
        for d in directions[probe.geometry]}


@pytest.mark.private_data  # pragma: no cover - needs data
def test_crowded_window_histograms_conserve_every_species(
        real_crowded_whole, private_window_files, real_histograms, study_spec,
        directions):
    """Every position of a crowded ``all`` window, crowders at the wall and
    in the corners included, falls inside the edges: each frame counts every
    particle of each species once."""
    probe = study_spec(real_crowded_whole.study).PROBE
    window, data = private_window_files(real_crowded_whole)
    counts = real_crowded_whole.window_counts()

    analysis = real_histograms(real_crowded_whole, data, window, 'all')

    assert _counted(analysis, probe.histogram_species,
                    directions[probe.geometry]) == {
        f"{d}{s}": ([counts[s]],
                    counts[s] * real_crowded_whole.n_window_frames)
        for s in probe.histogram_species
        for d in directions[probe.geometry]}
