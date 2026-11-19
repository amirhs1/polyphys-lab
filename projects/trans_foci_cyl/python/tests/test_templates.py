"""Tests for what is TransFociCyl's own in its LAMMPS part: its run names
against its parser, its start configurations, the shared relaxed chain,
and its resource tables.

These are consistency checks with no reference value. The checks that the
studies share are in ``tests/test_templates.py`` at the repository root.
"""
import csv
import re
import subprocess
from pathlib import Path

import pytest

from polyphys_lab.trans_foci_cyl.parser import TransFociCyl

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


def _sweep(variant: str) -> list[dict[str, str]]:
    """Return a variant's sweep rows, each as a mapping from column name
    to value; the comment line that opens ``SWEEP`` names the columns."""
    text = (LAMMPS / variant / "study.conf").read_text()
    match = re.search(r"^SWEEP=\(\n\s*#\s*(.+)$", text, re.MULTILINE)
    assert match is not None
    columns = match.group(1).split()
    rows = _table(variant, "SWEEP")
    assert all(len(row) == len(columns) for row in rows)
    return [dict(zip(columns, row)) for row in rows]


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
        parsed = TransFociCyl(row["run_name"], "whole", "all")
        values = {
            "epsilon_small": float(row["epsilon_small"]),
            "epsilon_large": float(row["epsilon_big"]),
            "dcyl": 2 * float(row["r"]) - 1,
            "lcyl": 2 * float(row["lz"]),
            "dmon_large": float(row["sig2"]),
            "nmon_large": int(row["n_big"]),
            "mmon_large": float(row["m_big"]),
            "nmon_small": int(row["n_small"]),
            "dcrowd": float(row["sig3"]),
            "ncrowd": int(row["n_crowd"]),
            "dt": float(row["run_dt"]),
            "bdump": int(row["bug_dump"]),
            "adump": int(row["all_dump"]),
            "ensemble_id": int(row["ens"]),
        }
        got = {attr: getattr(parsed, attr) for attr in values}
        if got != pytest.approx(values):
            mismatched.append(row["run_name"])
    assert mismatched == []


@pytest.mark.parametrize(
    "name", ["foci-ring-ns400nl5.data", "minimized.initial.config.data"])
def test_start_file_holds_the_ring(
        name: str, manifest: list[dict[str, str]]) -> None:
    """Each file of ``start/`` counts the monomers of every run, joined in
    a ring: as many bonds as atoms."""
    header = (LAMMPS / "start" / name).read_text()
    counts = dict(
        (key, int(value)) for value, key in
        re.findall(r"^(\d+) (atoms|bonds|atom types|bond types)$", header,
                   re.MULTILINE))
    monomers = {int(r["n_small"]) + int(r["n_big"]) for r in manifest}
    assert counts == {"atoms": 405, "bonds": 405, "atom types": 3,
                      "bond types": 2}
    assert monomers == {counts["atoms"]}


def test_shared_chain_has_the_box_and_sizes_of_its_runs() -> None:
    """The shared relaxed chain is in the cylinder of every run that reads
    it, and its input relaxes the chain of those runs: the same sizes,
    mass, and wall strengths."""
    text = (LAMMPS / "start" / "minimize.lmp").read_text()
    code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    state = {name: float(value) for name, value in re.findall(
        r"^\s*variable\s+(\w+)\s+equal\s+([\d.]+)\s*$", code, re.MULTILINE)}
    header = (LAMMPS / "start" / "minimized.initial.config.data").read_text()
    box = {axis: (float(low), float(high)) for low, high, axis in re.findall(
        r"^(\S+) (\S+) ([xyz])lo [xyz]hi$", header, re.MULTILINE)}
    rows = [row for variant in _variants() for row in _sweep(variant)
            if row.get("relax_steps") == "shared"]
    assert rows != []
    for row in rows:
        r, lz = float(row["r"]), float(row["lz"])
        assert box == {"x": (-r, r), "y": (-r, r), "z": (-lz, lz)}
        assert {name: state[name] for name in (
            "sig2", "mass2", "sig3", "r", "lz", "epsilon_small",
            "epsilon_big")} == pytest.approx({
                "sig2": float(row["sig2"]), "mass2": float(row["m_big"]),
                "sig3": float(row["sig3"]), "r": r, "lz": lz,
                "epsilon_small": float(row["epsilon_small"]),
                "epsilon_big": float(row["epsilon_big"])})


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
