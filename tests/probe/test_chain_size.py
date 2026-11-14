r"""Tests of :mod:`polyphys.probe.chain_size` on real frames.

The tests read the tier B and tier C files of the studies' wholes
(``tests/probe/conftest.py``, "Real frames"). Their expected values are
properties or other files of the same run: the chain measured in the ``all``
window at a time step the polymer dump shares, which holds the same
configuration; the FENE bound on a bond, :math:`R_0 = 1.5 \sigma`, far below
half the box, so a wrapped chain whose bonds are all shorter than half the box
is whole and unwrapping it changes nothing; the first level of the blocking
transform of Flyvbjerg and Petersen, J. Chem. Phys. 91, 461 (1989), whose
standard error is the naive one of the uncorrelated estimate; and, with the
maintainer's data, the research code's probe output of the same wholes.
"""
import numpy as np
import pytest
from numpy.testing import assert_allclose

from polyphys.analyze.stats import block_average

pytest.importorskip("MDAnalysis")

from polyphys.probe import ChainSize  # noqa: E402

# The dump reader warns that the frames carry no time step; the tests
# measure per frame and give no dt.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")

# Tolerances: MDAnalysis holds positions as float32, so a value carries a
# relative round-off of about 1e-7; 1e-6 leaves room for a few operations.
RTOL = 1e-6
ATOL = 1e-6


# Real frames


def _at_shared_steps(polymer, window, probe, trajectory_arrays):
    """The spec's observables of the chain in the polymer dump and in the
    window, at the time steps both hold, each flattened and joined in the
    spec's order; and the number of those steps."""
    polymer_steps = trajectory_arrays(polymer)['steps']
    window_steps = trajectory_arrays(window)['steps']
    shared = np.intersect1d(polymer_steps, window_steps)
    values = [
        ChainSize.from_spec(universe, probe).run(
            frames=np.flatnonzero(np.isin(steps, shared))).results
        for universe, steps in ((polymer, polymer_steps),
                                (window, window_steps))]
    return ([np.concatenate([result[obs].ravel()
                             for obs in probe.observables])
             for result in values], shared.size)


def test_real_chain_size_agrees_between_the_polymer_dump_and_the_window(
        real_window_whole, real_files, real_universe, study_spec,
        trajectory_arrays):
    """At every time step the polymer dump and the ``all`` window share,
    each chain-size observable of the spec is the same in both."""
    probe = study_spec(real_window_whole.study).PROBE
    files = real_files(real_window_whole)
    polymer = real_universe(files.topology, files.polymer)
    window = real_universe(files.data, files.window)

    (from_polymer, from_window), n_shared = _at_shared_steps(
        polymer, window, probe, trajectory_arrays)

    assert n_shared == real_window_whole.n_shared_frames
    assert_allclose(from_polymer, from_window, rtol=RTOL, atol=ATOL)


@pytest.mark.private_data  # pragma: no cover - needs data
def test_real_chain_size_agrees_with_the_crowded_window(
        real_crowded_whole, real_files, private_window_files, real_universe,
        study_spec, trajectory_arrays):
    """In a crowded whole, the polymer dump opened with the borrowed
    topology and the ``all`` window opened with the whole's own data file
    give the same chain-size observables at every shared time step."""
    probe = study_spec(real_crowded_whole.study).PROBE
    files = real_files(real_crowded_whole)
    window_path, data_path = private_window_files(real_crowded_whole)
    polymer = real_universe(files.topology, files.polymer)
    window = real_universe(data_path, window_path)

    (from_polymer, from_window), n_shared = _at_shared_steps(
        polymer, window, probe, trajectory_arrays)

    assert n_shared == real_crowded_whole.n_shared_frames
    assert_allclose(from_polymer, from_window, rtol=RTOL, atol=ATOL)


def test_real_chain_bonds_are_shorter_than_half_the_periodic_box(
        real_polymer_whole, real_files, real_universe, study_spec,
        trajectory_arrays):
    """In every frame of a polymer dump, every bond of the chain spans less
    than half the box along each periodic direction: the wrapping splits no
    chain. (Free H-NS proteins do cross the boundary of the periodic cube;
    their core-patch bonds are not checked.)"""
    probe = study_spec(real_polymer_whole.study).PROBE
    files = real_files(real_polymer_whole)
    universe = real_universe(files.topology, files.polymer)
    arrays = trajectory_arrays(universe)
    first, second = universe.select_atoms(
        probe.selections[probe.chain]).bonds.indices.T
    periodic = {'cubic': [0, 1, 2], 'cylindrical': [2]}[probe.geometry]

    spans = np.abs(arrays['positions'][:, first] -
                   arrays['positions'][:, second])[..., periodic]
    halves = 0.5 * arrays['boxes'][:, None, periodic]

    assert np.count_nonzero(spans >= halves) == 0


def test_real_asphericity_does_not_depend_on_unwrap(
        real_polymer_whole, real_files, real_universe, study_spec):
    """On real chains that no boundary splits, the asphericity is the same
    whether or not the chain is unwrapped first, in every study."""
    probe = study_spec(real_polymer_whole.study).PROBE
    files = real_files(real_polymer_whole)
    chain = real_universe(files.topology, files.polymer).select_atoms(
        probe.selections[probe.chain])

    wrapped, unwrapped = (
        ChainSize(chain, ('asphericityT',), unwrap=unwrap).run().results[
            'asphericityT'] for unwrap in (False, True))

    assert_allclose(unwrapped, wrapped, rtol=RTOL, atol=ATOL)


def test_block_average_of_a_real_gyration_series_starts_at_the_naive_error(
        real_polymer_whole, real_files, real_universe, study_spec):
    """Block averaging runs on the 50-frame radius-of-gyration series of a
    real chain, with finite errors at every level and the naive standard
    error at the first."""
    probe = study_spec(real_polymer_whole.study).PROBE
    files = real_files(real_polymer_whole)
    chain = real_universe(files.topology, files.polymer).select_atoms(
        probe.selections[probe.chain])
    series = ChainSize(chain, ('gyrT',)).run().results['gyrT']

    result = block_average(series)

    assert np.all(np.isfinite(result.sem))
    # Both are float64 reductions of the same 50 values.
    assert result.sem[0] == pytest.approx(
        series.std(ddof=1) / np.sqrt(series.size), rel=1e-12)


# Against the research code's probe (tier C)


@pytest.mark.private_data  # pragma: no cover - needs data
@pytest.mark.parametrize('observable', ['gyrT', 'shapeT', 'asphericityT'])
def test_real_chain_size_matches_the_research_code(
        real_transfocicub_whole, real_files, real_universe, study_spec,
        research_probe_file, observable):
    """On the 50 frames of a TransFociCub polymer dump, each scalar
    chain-size observable of the spec equals the research code's probe of
    the same frames (``trans_foci_cub_bug``)."""
    whole = real_transfocicub_whole
    probe = study_spec(whole.study).PROBE
    files = real_files(whole)
    universe = real_universe(files.topology, files.polymer)
    expected = np.load(research_probe_file(whole, f"{observable}Mon"))

    results = ChainSize.from_spec(universe, probe).run().results

    # The research code shifted the float32 positions by half the box
    # before measuring, and this probe recenters the chain, so the two
    # differ by the float32 round-off of coordinates of about 20: 1e-6.
    assert_allclose(results[observable], expected, rtol=RTOL, atol=ATOL)


@pytest.mark.private_data  # pragma: no cover - needs data
def test_real_principal_axes_match_the_research_code_up_to_sign(
        real_transfocicub_whole, real_files, real_universe, study_spec,
        research_probe_file):
    """On the 50 frames of a TransFociCub polymer dump, each frame's
    principal axes equal the research code's up to the sign of each axis,
    which the eigenvector solver sets arbitrarily."""
    whole = real_transfocicub_whole
    probe = study_spec(whole.study).PROBE
    files = real_files(whole)
    universe = real_universe(files.topology, files.polymer)
    expected = np.load(research_probe_file(whole, 'principalTMon'))

    axes = ChainSize.from_spec(universe, probe).run().results['principalT']

    # Per frame and axis, the smaller of |a - b| and |a + b|; the same
    # float32 round-off as the scalar observables.
    closest = np.minimum(np.linalg.norm(axes - expected, axis=-1),
                         np.linalg.norm(axes + expected, axis=-1))
    assert closest.shape == (50, 3)
    assert_allclose(closest, np.zeros_like(closest), rtol=0, atol=ATOL)
