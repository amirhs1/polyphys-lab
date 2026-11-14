"""Tests of :mod:`polyphys.analyze.pipeline` against the research code.

The tests reduce the TransFociCub study's probe output with its specs and
compare the result with the research code's: its ensemble averages, its
space time series, and, from the tier B frames in ``tests/data/probe/``,
a probe-and-reduce run of the same wholes. They are written blind and run
only with the maintainer's data.
"""
import dataclasses
import importlib
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from polyphys.analyze.pipeline import (
    Autocorrelation,
    reduce_space,
    space_tseries_from_spec,
)

# A Pandas4Warning marks a deprecated pandas call; fail on it.
pytestmark = pytest.mark.filterwarnings("error::pandas.errors.Pandas4Warning")


@pytest.fixture
def probe_dir(tmp_path):
    """A probe directory, ``<root>/probes/N-bug-probe``, next to which
    ``reduce_space`` writes ``<root>/analysis/``."""
    probe = tmp_path / "probes" / "N-bug-probe"
    probe.mkdir(parents=True)
    return probe


# Golden comparison with the research code, written blind


def _study_module():  # pragma: no cover - tier C helpers
    """The TransFociCub spec module, ``polyphys_lab.trans_foci_cub.spec``."""
    return importlib.import_module("polyphys_lab.trans_foci_cub.spec")


def _research_folder(private_data_dir, phase, suffix):  # pragma: no cover
    """The one ``TransFociCub/<phase>/*-bug-<suffix>`` folder of the research
    code's output under the data directory, or a skip."""
    parent = private_data_dir / "TransFociCub" / phase
    folders = sorted(parent.glob(f"*-bug-{suffix}"))
    if len(folders) != 1:
        pytest.skip(f"no single *-bug-{suffix} folder under {parent}")
    return folders[0]


def _bug_table(module):  # pragma: no cover
    """The study's analysis table of the ``bug`` group."""
    (table,) = [t for t in module.ANALYSIS if t.group == "bug"]
    return table


def _cap_autocorrelation_lags(table, n_frames):  # pragma: no cover
    """The table with each ``Autocorrelation`` hook's lags capped at
    ``n_frames - 1``. The research code's statsmodels ``acf`` clamped lags
    beyond the series silently, and PolyPhys's rejects them, so a fixture
    of short wholes needs the cap; the spec itself is unchanged."""
    return dataclasses.replace(table, properties=tuple(
        dataclasses.replace(prop, post_hook=Autocorrelation(
            min(prop.post_hook.nlags, n_frames - 1)))
        if isinstance(prop.post_hook, Autocorrelation) else prop
        for prop in table.properties))


def _assert_ens_avg_matches(produced, reference):  # pragma: no cover
    """Every ``*-ensAvg.csv`` of `produced` with a counterpart in `reference`
    equals it, to float64 round-off, and at least one does. The
    pair-distance artifacts and the ACF band are left out: they changed on
    purpose (criteria section 4), and the ACFs run on capped lags."""
    compared = 0
    for path in sorted(produced.glob("*-ensAvg.csv")):
        if "pairDist" in path.name or "-acf" in path.name:
            continue
        counterpart = reference / path.name
        if not counterpart.exists():
            continue
        pd.testing.assert_frame_equal(
            pd.read_csv(path), pd.read_csv(counterpart), rtol=1e-10,
            atol=1e-12, check_like=True)
        compared += 1
    assert compared > 0, f"no ensAvg file of {produced} has a counterpart"


@pytest.mark.private_data
def test_ens_avg_matches_the_research_code(  # pragma: no cover - needs data
        private_data_dir, tmp_path):
    """The ensemble averages of one TransFociCub space, reduced from the
    research code's probe output, match the research code's, for every
    property it reduced the same way.

    Expects ``<data>/TransFociCub/probes/<space>-bug-probe/`` (the probe
    phase of one space) and
    ``<data>/TransFociCub/analysis/<prefix>-bug-ensAvg/`` (the research
    code's ensemble averages). The probe folder is linked into a temporary
    tree so that nothing is written under the data directory.
    """
    module = _study_module()
    probe = _research_folder(private_data_dir, "probes", "probe")
    reference = _research_folder(private_data_dir, "analysis", "ensAvg")
    linked = tmp_path / "probes" / probe.name
    linked.parent.mkdir()
    linked.symlink_to(probe, target_is_directory=True)
    # The frame count from one whole's gyrTMon header, not its values.
    n_frames = np.load(next(probe.rglob("*-gyrTMon.npy")),
                       mmap_mode="r").shape[0]
    table = _cap_autocorrelation_lags(_bug_table(module), n_frames)

    reduce_space(linked, module.SPEC, table)

    produced = tmp_path / "analysis" / f"{probe.name.split('-')[0]}-bug-ensAvg"
    _assert_ens_avg_matches(produced, reference)


def _uncrowded(whole, wholes):  # pragma: no cover
    """The whole without crowders of the family and replicate of `whole`:
    the name that differs only in the crowder count and box side,
    ``nc<n>l<side>``, and has ``nc0``."""
    family = re.sub(r"nc\d+l[\d.]+", "", whole)
    (match,) = [other for other in wholes if "nc0l" in other
                and re.sub(r"nc\d+l[\d.]+", "", other) == family]
    return match


def _probe_tier_b_wholes(module, wholes, probe_dir):  # pragma: no cover
    """Probe each whole's tier B polymer dump (``polyphys/tests/data/probe/``)
    with the study's ``ProbeSpec``, opened with the data file of its whole
    without crowders, and save the chain-size observables, the foci pair
    quantities, and the stamps under the research names in
    ``probe_dir/<whole>.ring/``."""
    from polyphys.probe import (
        ChainSize, PairDistances, make_universe, write_stamps)

    data = Path(__file__).resolve().parents[1] / "data" / "probe"
    for whole in wholes:
        topology = _uncrowded(whole, wholes)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", "Reader has no dt information", UserWarning)
            universe = make_universe(
                data / topology / f"{topology}.ring.all.data.gz",
                data / whole / f"{whole}.ring.bug.last50.lammpstrj.gz")
        parser = module.SPEC.parser(f"{whole}.ring", "whole",
                                    module.SPEC.group)
        folder = probe_dir / f"{whole}.ring"
        folder.mkdir(parents=True)
        name = f"{parser.name}-{parser.group}"
        ChainSize.from_spec(universe, module.PROBE).run().save(folder, name)
        PairDistances.from_spec(universe, module.PROBE, parser).run().save(
            folder, name)
        write_stamps(parser, universe.trajectory.n_frames, folder)


@pytest.mark.private_data
@pytest.mark.filterwarnings(
    "ignore:Reader has no dt information:UserWarning")
def test_probe_and_reduce_match_the_research_ens_avg(  # pragma: no cover
        private_data_dir, tmp_path):
    """Probing the TransFociCub polymer dumps with the study's ``ProbeSpec``,
    saving under the research names, and reducing them with ``reduce_space``
    reproduces the research code's ensemble averages end to end. The wholes
    are those of the research probe folder; the dumps are their tier B
    copies, the same 50 frames the research probe read."""
    pytest.importorskip("MDAnalysis")
    module = _study_module()
    research = _research_folder(private_data_dir, "probes", "probe")
    reference = _research_folder(private_data_dir, "analysis", "ensAvg")
    wholes = sorted(path.name.removesuffix(".ring")
                    for path in research.iterdir() if path.is_dir())
    probe_dir = tmp_path / "probes" / research.name
    _probe_tier_b_wholes(module, wholes, probe_dir)
    # The tier B polymer dumps hold the wholes' last 50 frames.
    table = _cap_autocorrelation_lags(_bug_table(module), 50)

    reduce_space(probe_dir, module.SPEC, table)

    produced = (tmp_path / "analysis"
                / f"{research.name.split('-')[0]}-bug-ensAvg")
    _assert_ens_avg_matches(produced, reference)


@pytest.mark.private_data
@pytest.mark.parametrize("prop", ["gyrTMon", "shapeTMon", "asphericityTMon"])
def test_space_tseries_from_spec_matches_the_research_code(  # pragma: no cover
        private_data_dir, prop):
    """The space table of a TransFociCub time series, built from the
    research code's ensemble averages, equals the research code's space
    table: the same rows by state point and time index, the same
    statistics, time, and attributes, under the spec's renaming of the
    crowder volume fraction and the documented mapping of the short names
    (Usage, "Lineage names")."""
    spec = _study_module().SPEC
    ens_avg = _research_folder(private_data_dir, "analysis", "ensAvg")
    space_dir = _research_folder(private_data_dir, "analysis", "space")
    theirs = pd.read_csv(
        space_dir / f"{space_dir.name.split('-')[0]}-bug-{prop}-space.csv")
    theirs = theirs.rename(columns={"phi_c_bulk": "phi_bulk_c",
                                    "phi_c_bulk_round": "phi_bulk_c_round"})
    # A research short name, parsed at its lineage and rebuilt, gives the
    # current form.
    theirs = theirs.assign(**{
        lineage: theirs[lineage].map(
            lambda text, lineage=lineage: getattr(
                spec.parser(text, lineage, spec.group), lineage))
        for lineage in ("ensemble", "space")})
    key = ["ensemble_long", "t_index"]

    ours = space_tseries_from_spec(ens_avg, spec, prop)

    ours = ours.sort_values(key).reset_index(drop=True)
    theirs = theirs.sort_values(key).reset_index(drop=True)
    assert set(theirs.columns) <= set(ours.columns)
    # The statistics are float64 values read from the same CSV files; the
    # integer attributes compare exactly. The research table wrote some
    # attributes as integers that PolyPhys holds as floats, hence no dtype
    # check.
    pd.testing.assert_frame_equal(ours[theirs.columns], theirs, rtol=1e-10,
                                  atol=1e-12, check_dtype=False)
