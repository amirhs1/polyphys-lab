"""Tests of :mod:`polyphys.probe.pairs` on real frames.

The tests run the TransFoci studies' probe specs on the tier B polymer dumps of
their wholes (``tests/probe/conftest.py``, "Real frames"). Their expected
values are the foci's places along the ring in the data file, read with
:func:`polyphys.simulate.data.read_data`; the minimum-image distances of
``MDAnalysis.lib.distances.distance_array``; the conservation of the foci among
the bonds and the clusters; and, with the maintainer's data, the research
code's foci histograms.
"""
import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from polyphys.simulate.data import read_data

pytest.importorskip("MDAnalysis")

from polyphys.probe import PairDistances  # noqa: E402

# The dump reader warns that the frames carry no time step; the tests
# measure per frame and give no dt.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")


# Real frames


@pytest.fixture
def real_pairs(real_files, real_universe, study_spec):
    """Factory: the study's :meth:`PairDistances.from_spec` run on a real
    TransFoci polymer dump, with the universe it read."""

    def _run(whole):
        module = study_spec(whole.study)
        files = real_files(whole)
        universe = real_universe(files.topology, files.polymer)
        parser = module.SPEC.parser(f"{whole.whole}.ring", 'whole',
                                    whole.group)
        return (PairDistances.from_spec(universe, module.PROBE,
                                        parser).run(), universe)

    return _run


def test_real_foci_diagonal_holds_their_places_along_the_ring(
        real_foci_whole, real_files, real_pairs):
    """Every frame's diagonal holds the 0-based places of the large
    monomers along the ring, as the data file orders its atoms."""
    data = read_data(real_files(real_foci_whole).topology)
    expected = np.flatnonzero(data.types[data.mol_ids == 1] == 2)

    analysis, _ = real_pairs(real_foci_whole)

    assert_array_equal(
        np.diagonal(analysis.results['distMatTFoci'], axis1=1, axis2=2),
        np.tile(expected, (50, 1)))


def test_real_foci_distances_are_the_minimum_image_distances(
        real_foci_whole, real_pairs, study_spec, trajectory_arrays,
        reference_distances):
    """Above the diagonal, every frame holds the foci's minimum-image
    distances along the geometry's periodic directions."""
    probe = study_spec(real_foci_whole.study).PROBE

    analysis, universe = real_pairs(real_foci_whole)

    arrays = trajectory_arrays(universe)
    foci = arrays['positions'][:, analysis.atomgroup.indices]
    expected = reference_distances(foci, foci, arrays['boxes'],
                                   probe.geometry)
    upper = np.triu_indices(analysis.atomgroup.n_atoms, k=1)
    # float32 positions of at most about 165 carry a round-off of about
    # 1e-5 in a separation.
    assert_allclose(analysis.results['distMatTFoci'][:, upper[0], upper[1]],
                    expected[:, upper[0], upper[1]], rtol=0, atol=5e-5)


def test_real_foci_bonds_and_clusters_conserve_the_foci(real_foci_whole,
                                                        real_pairs):
    """In every frame, the bonds histogram counts each large monomer once
    and the clusters histogram, weighted by cluster size, does too."""
    analysis, _ = real_pairs(real_foci_whole)
    clusters = analysis.results['clustersHistTFoci']
    sizes = np.arange(clusters.shape[1])

    assert_array_equal(analysis.results['bondsHistTFoci'].sum(axis=1),
                       np.full(50, real_foci_whole.n_foci))
    assert_array_equal(clusters @ sizes, np.full(50, real_foci_whole.n_foci))


# Against the research code's probe (tier C)


@pytest.mark.private_data  # pragma: no cover - needs data
@pytest.mark.parametrize('histogram, sizes', [
    pytest.param('bondsHistTFoci', slice(None), id='bonds'),
    pytest.param('clustersHistTFoci', slice(1, None), id='clusters'),
])
def test_real_foci_histograms_match_the_research_code(
        real_transfocicub_whole, real_pairs, research_probe_file, histogram,
        sizes):
    """On the 50 frames of a TransFociCub polymer dump, the foci bonds
    histogram and the clusters histogram from size 1 up equal the research
    code's probe of the same frames (``trans_foci_cub_bug``), whose
    contacts took no minimum image: the ring is whole in these dumps, so
    the image changes no contact. The research clusters histogram counted
    the zero eigenvalues of the contact matrix in its size-0 column, which
    the analysis table drops; this probe writes no cluster of size 0."""
    analysis, _ = real_pairs(real_transfocicub_whole)
    expected = np.load(research_probe_file(real_transfocicub_whole, histogram))

    assert_array_equal(analysis.results[histogram][:, sizes],
                       expected[:, sizes])
