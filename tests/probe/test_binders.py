"""Tests of :mod:`polyphys.probe.binders` on real frames.

The tests run the H-NS studies' probe specs on the tier B polymer dumps of
their wholes (``tests/probe/conftest.py``, "Real frames"). Their expected
values are the identities the counts obey by definition, with the binder
numbers of the wholes' names and two patches per H-NS core, and the
minimum-image distances of ``MDAnalysis.lib.distances.distance_array``.
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

pytest.importorskip("MDAnalysis")

from polyphys.probe import BinderStatistics  # noqa: E402

# The dump reader warns that the frames carry no time step; the tests
# count per frame and give no dt.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")


# Real frames


@pytest.fixture
def real_binders(real_files, real_universe, study_spec):
    """Factory: the study's :meth:`BinderStatistics.from_spec` on a real Hns
    polymer dump, with the universe it reads; not yet run."""

    def _build(whole):
        files = real_files(whole)
        universe = real_universe(files.topology, files.polymer)
        return (BinderStatistics.from_spec(
            universe, study_spec(whole.study).PROBE), universe)

    return _build


def test_real_binding_counts_obey_their_identities(real_hns_whole,
                                                   real_binders):
    """In every real frame, each patch is free or engaged, each binder is
    free, dangling, or bridging, the loop histogram counts every distinct
    cis or trans pair, no more pairs than bridges form, and engaged patches
    make at least one contact each."""
    analysis, _ = real_binders(real_hns_whole)
    n_hns = real_hns_whole.n_hns

    results = analysis.run().results

    pairs = results['n_pairs_cis'] + results['n_pairs_trans']
    assert_array_equal(results['n_patches_free']
                       + results['n_patches_engaged'], np.full(50, 2 * n_hns))
    assert_array_equal(results['n_binders_free']
                       + results['n_binders_dangling']
                       + results['n_binders_bridging'], np.full(50, n_hns))
    assert_array_equal(results['loop_length_histogram'].sum(axis=1), pairs)
    assert np.all(pairs <= results['n_binders_bridging'])
    assert np.all(results['n_patch_monomer_contacts']
                  >= results['n_patches_engaged'])


def test_real_binder_distances_are_the_minimum_image_distances(
        real_hns_whole, real_binders, study_spec, trajectory_arrays,
        reference_distances):
    """The stored monomer-to-patch distances of every real frame are the
    minimum-image distances along the geometry's periodic directions."""
    probe = study_spec(real_hns_whole.study).PROBE
    analysis, universe = real_binders(real_hns_whole)

    distances = analysis.run().results['distances']

    arrays = trajectory_arrays(universe)
    expected = reference_distances(
        arrays['positions'][:, analysis.chain.indices],
        arrays['positions'][:, analysis.patches.indices], arrays['boxes'],
        probe.geometry)
    # float32 positions of at most about 150 carry a round-off of about
    # 1e-5 in a separation.
    assert_allclose(distances, expected, rtol=0, atol=5e-5)


def test_real_whole_without_hns_has_no_binders_to_count(real_nh0_whole,
                                                        real_binders):
    """A real Hns whole without H-NS proteins has no patches, which the
    binder analysis rejects."""
    with pytest.raises(ValueError, match="positive multiple of 2"):
        real_binders(real_nh0_whole)
