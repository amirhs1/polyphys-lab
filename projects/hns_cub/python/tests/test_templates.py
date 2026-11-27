"""Tests for what is HnsCub's own in its LAMMPS part: the molecule file
its production reads, its run names against its parser, its start
configuration, the H-NS molecule, and its resource table.

These are consistency checks with no reference value. The checks that the
studies share are in ``tests/test_templates.py`` at the repository root.
"""
import csv
import re
import subprocess
from pathlib import Path

import pytest

from polyphys_lab.hns_cub.parser import HnsCub

STUDY = Path(__file__).resolve().parents[2]
LAMMPS = STUDY / "lammps"
START = LAMMPS / "start"
MOLECULE = re.compile(r"^\s*molecule\s+\S+\s+(\S+)", re.MULTILINE)


def _variants() -> list[str]:
    """Return the variants: the folders of ``lammps/`` with a
    ``study.conf``."""
    return sorted(p.parent.name for p in LAMMPS.glob("*/study.conf"))


def _table(variant: str, name: str) -> list[list[str]]:
    """Return the rows of the bash array `name` in a variant's
    ``study.conf``, split; a plain variable gives one row, and a variable
    that is not set gives none."""
    script = f'source "$1"; printf "%s\\n" "${{{name}[@]}}"'
    result = subprocess.run(
        ["bash", "-c", script, "_", str(LAMMPS / variant / "study.conf")],
        check=True, capture_output=True, text=True)
    return [line.split() for line in result.stdout.splitlines() if line]


def _code(text: str) -> str:
    """Return a LAMMPS input without its comments."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _header(text: str) -> dict[str, int]:
    """Return the counts of a LAMMPS data or molecule file's header, such
    as ``atoms`` and ``bond types``."""
    return {key: int(value) for value, key in re.findall(
        r"^\s*(\d+)\s+(atoms|bonds|angles|atom types|bond types|"
        r"angle types)\s*$", text, re.MULTILINE)}


def _section(text: str, name: str) -> list[list[str]]:
    """Return the rows of a section of a LAMMPS data or molecule file, each
    split, up to the next section."""
    lines = text.splitlines()
    start = lines.index(name) + 1
    rows: list[list[str]] = []
    for line in lines[start:]:
        words = line.split("#", 1)[0].split()
        if not words:
            if rows:
                break
            continue
        if not words[0].lstrip("-").replace(".", "").isdigit():
            break
        rows.append(words)
    return rows


@pytest.fixture
def manifest() -> list[dict[str, str]]:
    """Return the rows of ``runs/manifest.csv``."""
    with open(STUDY / "runs" / "manifest.csv", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize("variant", _variants())
def test_production_reads_the_molecule_file(variant: str) -> None:
    """A variant's ``production.lmp`` reads the molecule file that
    ``MOLECULE_DATA`` names, and ``start/`` holds it."""
    [[molecule]] = _table(variant, "MOLECULE_DATA")
    assert MOLECULE.findall(
        (LAMMPS / variant / "production.lmp").read_text()) == [molecule]
    assert (START / molecule).is_file()


def test_manifest_names_parse_to_their_rows(
        manifest: list[dict[str, str]]) -> None:
    """Each run name parses, as a whole, to the values of its row."""
    mismatched = []
    for row in manifest:
        parsed = HnsCub(row["run_name"], "whole", "all")
        values = {
            "nmon": int(row["N"]),
            "bend_mm": float(row["kBend11"]),
            "nhns": int(row["n_hns"]),
            "dcrowd": float(row["sig4"]),
            "eps_hc": float(row["eps34"]),
            "ncrowd": int(row["n_crowd"]),
            "lcube": 2 * float(row["l"]),
            "ensemble_id": int(row["ens"]),
        }
        got = {attr: getattr(parsed, attr) for attr in values}
        if got != pytest.approx(values):
            mismatched.append(row["run_name"])
    assert mismatched == []


def test_start_file_holds_the_ring_of_every_run(
        manifest: list[dict[str, str]]) -> None:
    """The start file holds one ring of as many monomers as every run has:
    one bond and one angle per monomer, and one type of each."""
    counts = _header((START / "dna.data").read_text())
    assert counts == {"atoms": counts["atoms"], "bonds": counts["atoms"],
                      "angles": counts["atoms"], "atom types": 1,
                      "bond types": 1, "angle types": 1}
    assert {int(row["N"]) for row in manifest} == {counts["atoms"]}


def test_start_file_fits_in_every_cube(
        manifest: list[dict[str, str]]) -> None:
    """Every monomer of the start file lies inside the cube of every run,
    which ``change_box`` sets after the file is read."""
    atoms = _section((START / "dna.data").read_text(), "Atoms")
    reach = max(abs(float(x)) for atom in atoms for x in atom[3:6])
    assert reach < min(float(row["l"]) for row in manifest)


def test_molecule_is_a_core_between_two_poles() -> None:
    """The H-NS molecule has three atoms on an axis, two of one type around
    one of another, joined by two bonds and one angle, which production
    shifts to the pole, core, and bond and angle types it sets up."""
    text = (START / "hns.mol").read_text()
    assert _header(text) == {"atoms": 3, "bonds": 2, "angles": 1}
    types = [int(t) for _, t in _section(text, "Types")]
    assert types[0] == types[2] != types[1]
    coords = [[float(x) for x in c[1:]] for c in _section(text, "Coords")]
    assert coords[1] == [0.0, 0.0, 0.0]
    assert coords[0] == [-x for x in coords[2]]
    production = _code((LAMMPS / "wca_patch" / "production.lmp").read_text())
    assert re.search(r"^\s*molecule\s+\S+\s+hns\.mol\s+toff\s+1\s+boff\s+1"
                     r"\s+aoff\s+1\s*$", production, re.MULTILINE)
    assert re.search(r"^\s*group\s+hns_pole\s+type\s+"
                     rf"{types[0] + 1}\s*$", production, re.MULTILINE)
    assert re.search(r"^\s*group\s+hns_core\s+type\s+"
                     rf"{types[1] + 1}\s*$", production, re.MULTILINE)


def test_resources_cover_every_run(manifest: list[dict[str, str]]) -> None:
    """Every crowded run falls in a size class of its variant's
    ``RESOURCES``, counting crowders and DNA monomers."""
    uncovered = []
    for variant in _variants():
        largest = max(int(row[0]) for row in _table(variant, "RESOURCES"))
        sizes = [int(r["n_crowd"]) + int(r["N"]) for r in manifest
                 if r["variant"] == variant and r["n_crowd"] != "0"]
        if max(sizes) > largest:
            uncovered.append(variant)
    assert uncovered == []
