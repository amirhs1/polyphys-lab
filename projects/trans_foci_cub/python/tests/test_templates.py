"""Tests for the TransFociCub LAMMPS inputs, each variant's ``study.conf``,
and ``runs/manifest.csv``.

These are consistency checks with no reference value: every input is one
whole file that reads only variables it defines or that a pipeline stage
writes, each variant's inputs name the files they pass on, the manifest is
the expansion of the variants' sweeps, and every run name parses back to
its row.
"""
import csv
import re
import subprocess
from pathlib import Path

import pytest

from polyphys_lab.trans_foci_cub.parser import TransFociCub

STUDY = Path(__file__).resolve().parents[2]
LAMMPS = STUDY / "lammps"
VARIABLE_USE = re.compile(r"\$\{(\w+)\}|\$(\w)")
VARIABLE_DEFINITION = re.compile(r"^\s*variable\s+(\w+)\s", re.MULTILINE)
READ_DATA = re.compile(r"^\s*read_data\s+(\S+)", re.MULTILINE)
WRITE_DATA = re.compile(r"^\s*write_data\s+(\S+)", re.MULTILINE)


def _variants() -> list[str]:
    """Return the variants: the folders of ``lammps/`` with a
    ``study.conf``."""
    return sorted(p.parent.name for p in LAMMPS.glob("*/study.conf"))


def _inputs() -> list[Path]:
    """Return every LAMMPS input of the study."""
    return sorted(LAMMPS.glob("*/*.lmp"))


def _input_id(path: Path) -> str:
    """Return an input's test id: its variant and its name."""
    return f"{path.parent.name}/{path.name}"


def _table(variant: str, name: str) -> list[list[str]]:
    """Return the rows of the bash array `name` in a variant's
    ``study.conf``, split; a plain variable gives one row."""
    script = f'source "$1"; printf "%s\\n" "${{{name}[@]}}"'
    result = subprocess.run(
        ["bash", "-c", script, "_", str(LAMMPS / variant / "study.conf")],
        check=True, capture_output=True, text=True)
    return [line.split() for line in result.stdout.splitlines()]


def _code(text: str) -> str:
    """Return a LAMMPS input without its comments."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _used(text: str) -> set[str]:
    """Return the names of the variables that a LAMMPS input reads."""
    return {a or b for a, b in VARIABLE_USE.findall(_code(text))}


def _defined(text: str) -> set[str]:
    """Return the names of the variables that a LAMMPS input defines."""
    return set(VARIABLE_DEFINITION.findall(text))


def _first_input(variant: str) -> Path:
    """Return the input of a variant that starts from the start
    configuration: ``minimize.lmp``, or ``production.lmp`` where there is
    none."""
    minimize = LAMMPS / variant / "minimize.lmp"
    return minimize if minimize.is_file() else minimize.with_name(
        "production.lmp")


@pytest.fixture
def row_variables() -> set[str]:
    """Return the variables the sweep generator writes from a run's row."""
    return {"sig2", "n_big", "mass2", "n_small", "sig3", "n_crowd", "l",
            "i", "randseed", "run_dt", "bug_dump", "all_dump",
            "neigh_style", "neigh_skin", "relax_steps"}


@pytest.fixture
def stage_variables() -> dict[str, set[str]]:
    """Return the variables the restart stages add, by input name."""
    return {"restart.lmp": {"restart_file", "nloop", "last_loop_steps"},
            "continue.lmp": {"restart_file", "nloop"}}


@pytest.fixture
def manifest() -> list[dict[str, str]]:
    """Return the rows of ``runs/manifest.csv``."""
    with open(STUDY / "runs" / "manifest.csv", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize("path", _inputs(), ids=_input_id)
def test_input_reads_only_supplied_variables(
        path: Path, row_variables: set[str],
        stage_variables: dict[str, set[str]]) -> None:
    """An input reads only variables that it defines, that the generator
    writes from the run's sweep row, or that its restart stage adds."""
    text = path.read_text()
    supplied = row_variables | stage_variables.get(path.name, set())
    assert _used(text) - _defined(text) - supplied == set()


@pytest.mark.parametrize("path", _inputs(), ids=_input_id)
def test_input_is_one_whole_file(path: Path) -> None:
    """An input includes no other file: what a run does is in one place."""
    assert re.findall(r"^\s*include\s+\S+", _code(path.read_text()),
                      re.MULTILINE) == []


@pytest.mark.parametrize("path", _inputs(), ids=_input_id)
def test_run_lengths_are_variables(path: Path) -> None:
    """No input fixes a step count, a loop count, or a restart period as a
    number."""
    literal = re.compile(r"\brun\s+\d|^\s*restart\s+\d|\bloop\s+\d",
                         re.MULTILINE)
    assert literal.findall(_code(path.read_text())) == []


def test_variant_folders_are_the_manifest_variants(
        manifest: list[dict[str, str]]) -> None:
    """The folders with a ``study.conf`` are the variants the manifest
    names; each has a ``production.lmp`` and names itself in ``VARIANT``."""
    assert set(_variants()) == {row["variant"] for row in manifest}
    assert [v for v in _variants()
            if not (LAMMPS / v / "production.lmp").is_file()] == []
    assert [_table(v, "VARIANT") for v in _variants()] == [
        [[v]] for v in _variants()]


def test_first_input_reads_the_start_file() -> None:
    """The input of each variant that starts from the start configuration
    reads the file that ``START_DATA`` names, and ``start/`` holds it."""
    wrong = []
    for variant in _variants():
        [[start]] = _table(variant, "START_DATA")
        read = READ_DATA.findall(_first_input(variant).read_text())
        if read != [start] or not (LAMMPS / "start" / start).is_file():
            wrong.append(variant)
    assert wrong == []


def test_production_reads_what_minimize_writes() -> None:
    """Where a variant relaxes the chain first, ``production.lmp`` reads
    the data file that ``minimize.lmp`` writes."""
    wrong = []
    for variant in _variants():
        minimize = LAMMPS / variant / "minimize.lmp"
        if not minimize.is_file():
            continue
        written = WRITE_DATA.findall(minimize.read_text())
        read = READ_DATA.findall(
            minimize.with_name("production.lmp").read_text())
        if len(written) != 1 or read != written:
            wrong.append(variant)
    assert wrong == []


def test_sweep_rows_name_a_neighbor_style_the_inputs_set_up() -> None:
    """Every sweep row names ``bin`` or ``multi`` neighbor lists, the two
    styles the inputs set up."""
    styles = {row[12] for v in _variants() for row in _table(v, "SWEEP")}
    assert styles <= {"bin", "multi"}


def test_manifest_is_the_expanded_sweeps(
        manifest: list[dict[str, str]]) -> None:
    """``runs/manifest.csv`` lists each variant's sweep rows once per
    replicate, with the seed ``seed_group + ens`` and the row's own
    settings."""
    expected = []
    for variant in dict.fromkeys(row["variant"] for row in manifest):
        for (sig2, n_big, m_big, n_small, l, sig3, n_crowd, seed, dt,
             bdump, adump, ens, neigh, skin, relax) in _table(
                 variant, "SWEEP"):
            first, last = (int(e) for e in ens.split("-"))
            for i in range(first, last + 1):
                name = (f"al{sig2}nl{n_big}ml{m_big}ns{n_small}ac{sig3}"
                        f"nc{n_crowd}l{l}dt{dt}bdump{bdump}adump{adump}"
                        f"ens{i}.ring")
                expected.append(
                    [variant, name, sig2, n_big, m_big, n_small, sig3,
                     n_crowd, l, dt, bdump, adump, str(i),
                     str(int(seed) + i), neigh, skin, relax])
    assert [list(row.values()) for row in manifest] == expected


def test_manifest_identifies_each_run_once(
        manifest: list[dict[str, str]]) -> None:
    """No two manifest rows share a variant and a run name."""
    keys = [(row["variant"], row["run_name"]) for row in manifest]
    assert len(keys) == len(set(keys))


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
