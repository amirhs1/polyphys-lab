"""Tests for what is TransFociCub's own in its LAMMPS part: its run names
against its parser, its start configuration, and its resource table.

These are consistency checks with no reference value. The checks that the
studies share are in ``tests/test_templates.py`` at the repository root.
"""
import csv
import re
import subprocess
from pathlib import Path

import pytest

from polyphys_lab.trans_foci_cub.parser import TransFociCub

STUDY = Path(__file__).resolve().parents[2]
LAMMPS = STUDY / "lammps"


def _variants() -> list[str]:
    """Return the variants: the folders of ``lammps/`` with a
    ``study.conf``."""
    return sorted(p.parent.name for p in LAMMPS.glob("*/study.conf"))


def _table(variant: str, name: str) -> list[list[str]]:
    """Return the rows of the bash array `name` in a variant's
    ``study.conf``, split."""
    script = f'source "$1"; printf "%s\\n" "${{{name}[@]}}"'
    result = subprocess.run(
        ["bash", "-c", script, "_", str(LAMMPS / variant / "study.conf")],
        check=True, capture_output=True, text=True)
    return [line.split() for line in result.stdout.splitlines() if line]


@pytest.fixture
def manifest() -> list[dict[str, str]]:
    """Return the rows of ``runs/manifest.csv``."""
    with open(STUDY / "runs" / "manifest.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def test_manifest_names_parse_to_their_rows(
        manifest: list[dict[str, str]]) -> None:
    """Each run name parses, as a whole, to the values of its row."""
    mismatched = []
    for row in manifest:
        parsed = TransFociCub(row["run_name"], "whole", "all")
        values = {
            "dmon_large": float(row["sig2"]),
            "nmon_large": int(row["n_big"]),
            "mmon_large": float(row["m_big"]),
            "nmon_small": int(row["n_small"]),
            "dcrowd": float(row["sig3"]),
            "ncrowd": int(row["n_crowd"]),
            "lcube": 2 * float(row["l"]),
            "dt": float(row["run_dt"]),
            "bdump": int(row["bug_dump"]),
            "adump": int(row["all_dump"]),
            "ensemble_id": int(row["ens"]),
        }
        got = {attr: getattr(parsed, attr) for attr in values}
        if got != pytest.approx(values):
            mismatched.append(row["run_name"])
    assert mismatched == []


def test_start_file_holds_the_ring(manifest: list[dict[str, str]]) -> None:
    """The start file's header counts the monomers of every run, joined in
    a ring: as many bonds as atoms."""
    header = (LAMMPS / "start" / "foci-ring-ns400nl5.data").read_text()
    counts = dict(
        (key, int(value)) for value, key in
        re.findall(r"^(\d+) (atoms|bonds|atom types|bond types)$", header,
                   re.MULTILINE))
    monomers = {int(r["n_small"]) + int(r["n_big"]) for r in manifest}
    assert counts == {"atoms": 405, "bonds": 405, "atom types": 3,
                      "bond types": 2}
    assert monomers == {counts["atoms"]}


def test_resources_cover_every_run(manifest: list[dict[str, str]]) -> None:
    """Every crowded run falls in a size class of its variant's
    ``RESOURCES``."""
    uncovered = []
    for variant in _variants():
        largest = max(int(row[0]) for row in _table(variant, "RESOURCES"))
        sizes = [int(r["n_crowd"]) + int(r["n_small"]) + int(r["n_big"])
                 for r in manifest
                 if r["variant"] == variant and r["n_crowd"] != "0"]
        if max(sizes) > largest:
            uncovered.append(variant)
    assert uncovered == []
