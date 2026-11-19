"""Tests of :mod:`polyphys.probe.core` on real frames.

The tests read the tier B and tier C files of the studies' wholes
(``tests/probe/conftest.py``, "Real frames"). Their expected values are the
particle counts in the wholes' names, which each selection of a study's probe
spec must pick; the values a whole's name encodes, which its stamps must carry;
the data file of a crowded whole, read with
:func:`polyphys.simulate.data.read_data`; and, with the maintainer's data, the
research code's stamps.
"""

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from polyphys.simulate.data import read_data

pytest.importorskip("MDAnalysis")

from polyphys.probe import write_stamps  # noqa: E402

# The dump reader warns that the frames carry no time step; the tests that
# give no dt measure per frame.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")


def test_spec_selections_pick_the_species_of_a_real_polymer_dump(
        real_polymer_whole, real_files, real_universe, study_spec):
    """Each selection of the study's probe spec picks, in the polymer dump,
    the atoms the whole's name gives its species."""
    probe = study_spec(real_polymer_whole.study).PROBE
    files = real_files(real_polymer_whole)
    universe = real_universe(files.topology, files.polymer)

    counts = {species: universe.select_atoms(selection).n_atoms
              for species, selection in probe.selections.items()}

    assert counts == real_polymer_whole.polymer_counts()


def test_spec_selections_pick_the_species_of_a_real_window(
        real_window_whole, real_files, real_universe, study_spec):
    """Each selection of the study's probe spec picks, in the ``all``
    window, the atoms the whole's name gives its species, crowders
    included."""
    probe = study_spec(real_window_whole.study).PROBE
    files = real_files(real_window_whole)
    universe = real_universe(files.data, files.window)

    counts = {species: universe.select_atoms(selection).n_atoms
              for species, selection in probe.selections.items()}

    assert counts == real_window_whole.window_counts()


@pytest.mark.parametrize('study, whole, expected', [
    pytest.param('hns_cub', 'N200kbmm2nh30ac2l25epshc1nc10743ens1',
                 {'nmon': 200, 'nhns': 30, 'dcrowd': 2.0, 'lcube': 50.0,
                  'eps_hc': 1.0, 'ncrowd': 10743, 'ensemble_id': 1},
                 id='HnsCub'),
    pytest.param('trans_foci_cub',
                 'al6nl5ml216ns400ac1nc112776l27dt0.005bdump2000adump5000'
                 'ens1',
                 {'dmon_large': 6.0, 'nmon_large': 5, 'mmon_large': 216.0,
                  'nmon_small': 400, 'ncrowd': 112776, 'lcube': 54.0},
                 id='TransFociCub'),
    pytest.param('trans_foci_cyl',
                 'epss5epsl5r10.5al6nl5ml216ns400ac1nc0lz82.5dt0.005'
                 'bdump2000adump5000ens2',
                 {'dmon_large': 6.0, 'nmon_small': 400, 'ncrowd': 0,
                  'dcyl': 20.0, 'lcyl': 165.0, 'ensemble_id': 2},
                 id='TransFociCyl'),
])
def test_write_stamps_of_a_real_whole_carry_its_name(
        study_spec, tmp_path, study, whole, expected):
    """The stamps of a real whole hold the values its name encodes and the
    50 frames of its polymer dump."""
    spec = study_spec(study).SPEC
    parser = spec.parser(f"{whole}.ring", 'whole', spec.group)

    stamps = pd.read_csv(write_stamps(parser, 50, tmp_path))

    assert {key: stamps.loc[0, key] for key in expected} == expected
    # A whole's lineage name never carries the topology suffix ``.ring``
    # (ParserBase._set_parents).
    assert (stamps.loc[0, 'whole'], int(stamps.loc[0, 'n_frames'])) == (
        whole, 50)


@pytest.mark.private_data  # pragma: no cover - needs data
def test_borrowed_topology_is_the_crowded_whole_own_polymer_topology(
        real_crowded_whole, real_files, private_window_files):
    """The polymer atoms of a crowded whole's own data file have the IDs,
    types, molecule IDs, masses, and bonds of the data file its polymer
    dump borrows."""
    _, own_path = private_window_files(real_crowded_whole)
    borrowed = read_data(real_files(real_crowded_whole).topology)
    own = read_data(own_path)
    n_polymer = borrowed.n_atoms
    in_polymer = np.all(own.bonds[:, 1:] <= n_polymer, axis=1)

    def as_set(bonds):
        # Each run's write_data numbers its bonds in its own order, so the
        # bonds are compared as a set: sorted by type and atoms.
        return bonds[np.lexsort((bonds[:, 2], bonds[:, 1], bonds[:, 0]))]

    assert_array_equal(own.ids[:n_polymer], borrowed.ids)
    assert_array_equal(own.types[:n_polymer], borrowed.types)
    assert_array_equal(own.mol_ids[:n_polymer], borrowed.mol_ids)
    assert_array_equal(own.masses[borrowed.types - 1],
                       borrowed.masses[borrowed.types - 1])
    assert_array_equal(as_set(own.bonds[in_polymer]),
                       as_set(borrowed.bonds))


@pytest.mark.private_data  # pragma: no cover - needs data
def test_write_stamps_of_a_real_whole_match_the_research_code(
        real_transfocicub_whole, study_spec, research_probe_file, tmp_path):
    """The stamps of a TransFociCub whole hold the research code's lineage
    names under the documented mapping (Usage, "Lineage names"), the same
    attribute values under the spec's renaming, every research attribute
    but ``eps_others``, and the 50 frames the research probe counted."""
    whole = real_transfocicub_whole
    spec = study_spec(whole.study).SPEC
    parser = spec.parser(f"{whole.whole}.ring", 'whole', spec.group)
    theirs = pd.read_csv(research_probe_file(whole, 'stamps', ext='csv'))
    # The research names of the bulk fractions and densities and their
    # PolyPhys names (projects/trans_foci_cub/spec.py, module docstring).
    renamed = {'phi_c_bulk': 'phi_bulk_c', 'rho_c_bulk': 'rho_bulk_c',
               'phi_m_bulk': 'phi_bulk_m', 'rho_m_bulk': 'rho_bulk_m'}
    names = ('lineage_name', 'whole', 'ensemble_long', 'ensemble', 'space')

    ours = pd.read_csv(write_stamps(parser, 50, tmp_path))

    # A research whole name keeps ``.ring``; a short name parsed at its
    # lineage and rebuilt gives the current form.
    assert ours.loc[0, 'whole'] == theirs.loc[0, 'whole'].removesuffix(
        '.ring')
    assert ours.loc[0, 'ensemble_long'] == theirs.loc[0, 'ensemble_long']
    assert {lineage: ours.loc[0, lineage] for lineage in ('ensemble', 'space')
            } == {lineage: getattr(spec.parser(theirs.loc[0, lineage],
                                               lineage, spec.group), lineage)
                  for lineage in ('ensemble', 'space')}
    attributes = [column for column in theirs.columns
                  if column not in names and column != 'n_frames']
    unmatched = [column for column in attributes
                 if renamed.get(column, column) not in ours.columns]
    assert unmatched == ['eps_others']
    matched = [column for column in attributes if column not in unmatched]
    # Both codes compute the fractions in float64 from the same integers.
    assert_allclose(
        ours.loc[0, [renamed.get(column, column) for column in matched]]
        .to_numpy(dtype=float),
        theirs.loc[0, matched].to_numpy(dtype=float), rtol=1e-12, atol=0)
    assert int(theirs.loc[0, 'n_frames']) == int(ours.loc[0, 'n_frames']) == 50
