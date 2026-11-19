"""Tests for the TransFociCyl LAMMPS inputs, each variant's ``study.conf``,
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

from polyphys_lab.trans_foci_cyl.parser import TransFociCyl

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
    """Return an input's test id: its folder and its name."""
    return f"{path.parent.name}/{path.name}"


def _table(variant: str, name: str) -> list[list[str]]:
    """Return the rows of the bash array `name` in a variant's
    ``study.conf``, split; a plain variable gives one row, and a variable
    that is not set gives none."""
    script = f'source "$1"; printf "%s\\n" "${{{name}[@]}}"'
    result = subprocess.run(
        ["bash", "-c", script, "_", str(LAMMPS / variant / "study.conf")],
        check=True, capture_output=True, text=True)
    return [line.split() for line in result.stdout.splitlines() if line]


def _columns(variant: str) -> list[str]:
    """Return the column names of a variant's ``SWEEP``: the comment line
    that opens the table."""
    text = (LAMMPS / variant / "study.conf").read_text()
    match = re.search(r"^SWEEP=\(\n\s*#\s*(.+)$", text, re.MULTILINE)
    assert match is not None
    return match.group(1).split()


def _sweep(variant: str) -> list[dict[str, str]]:
    """Return a variant's sweep rows, each as a mapping from column name
    to value."""
    columns = _columns(variant)
    rows = _table(variant, "SWEEP")
    assert all(len(row) == len(columns) for row in rows)
    return [dict(zip(columns, row)) for row in rows]


def _code(text: str) -> str:
    """Return a LAMMPS input without its comments."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _used(text: str) -> set[str]:
    """Return the names of the variables that a LAMMPS input reads."""
    return {a or b for a, b in VARIABLE_USE.findall(_code(text))}


def _defined(text: str) -> set[str]:
    """Return the names of the variables that a LAMMPS input defines."""
    return set(VARIABLE_DEFINITION.findall(text))


def _value(text: str, pattern: str) -> str:
    """Return the one value that `pattern` captures in a LAMMPS input's
    commands."""
    [value] = re.findall(pattern, _code(text), re.MULTILINE)
    return str(value)


def _written_in_inputs(variant: str) -> dict[str, str]:
    """Return the settings that a variant's inputs write themselves: the
    manifest columns that its sweep does not carry."""
    production = (LAMMPS / variant / "production.lmp").read_text()
    minimize = (LAMMPS / variant / "minimize.lmp").read_text()
    patterns = {
        "neigh_style": (production, r"^\s*neighbor\s+\S+\s+(\w+)"),
        "neigh_skin": (
            production, r"^\s*variable\s+neigh_skin\s+equal\s+(\S+)"),
        "relax_steps": (
            minimize, r"^\s*variable\s+relax_steps\s+index\s+(\d+)"),
        "eq1_dt": (production, r"\A(?:.*\n)*?\s*timestep\s+(\S+)"),
        "restart_every": (
            production, r"^\s*variable\s+restart_every\s+index\s+(\d+)"),
    }
    return {name: _value(text, pattern)
            for name, (text, pattern) in patterns.items()
            if name not in _columns(variant)}


@pytest.fixture
def generator_names() -> dict[str, str]:
    """Return the sweep columns that the generator writes under another
    variable name."""
    return {"m_big": "mass2", "ens": "i", "seed_group": "randseed"}


@pytest.fixture
def manifest() -> list[dict[str, str]]:
    """Return the rows of ``runs/manifest.csv``."""
    with open(STUDY / "runs" / "manifest.csv", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize("path", _inputs(), ids=_input_id)
def test_input_reads_only_supplied_variables(
        path: Path, generator_names: dict[str, str]) -> None:
    """An input reads only variables that it defines or that the generator
    writes from the sweep row of its variant; the input of ``start/`` reads
    none from a row."""
    text = path.read_text()
    supplied = set()
    if path.parent.name in _variants():
        supplied = {generator_names.get(column, column)
                    for column in _columns(path.parent.name)}
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


def test_minimize_reads_the_start_file() -> None:
    """Each variant's ``minimize.lmp`` reads the file that ``START_DATA``
    names, and ``start/`` holds it."""
    wrong = []
    for variant in _variants():
        [[start]] = _table(variant, "START_DATA")
        read = READ_DATA.findall(
            (LAMMPS / variant / "minimize.lmp").read_text())
        if read != [start] or not (LAMMPS / "start" / start).is_file():
            wrong.append(variant)
    assert wrong == []


def test_production_reads_what_minimize_writes() -> None:
    """Each variant's ``production.lmp`` reads the data file that its
    ``minimize.lmp`` writes."""
    wrong = []
    for variant in _variants():
        written = WRITE_DATA.findall(
            (LAMMPS / variant / "minimize.lmp").read_text())
        read = READ_DATA.findall(
            (LAMMPS / variant / "production.lmp").read_text())
        if len(written) != 1 or read != written:
            wrong.append(variant)
    assert wrong == []


def test_shared_chain_is_what_production_reads() -> None:
    """A variant with a row whose ``relax_steps`` is ``shared`` names a
    ``RELAXED_DATA`` that ``start/`` holds, that ``start/minimize.lmp``
    writes from the start file, and that its ``production.lmp`` reads."""
    start_input = (LAMMPS / "start" / "minimize.lmp").read_text()
    wrong = []
    for variant in _variants():
        shared = [row for row in _sweep(variant)
                  if row.get("relax_steps") == "shared"]
        relaxed = _table(variant, "RELAXED_DATA")
        if not shared and not relaxed:
            continue
        [[start]] = _table(variant, "START_DATA")
        read = READ_DATA.findall(
            (LAMMPS / variant / "production.lmp").read_text())
        if (not shared or len(relaxed) != 1 or read != relaxed[0]
                or WRITE_DATA.findall(start_input) != relaxed[0]
                or READ_DATA.findall(start_input) != [start]
                or not (LAMMPS / "start" / relaxed[0][0]).is_file()):
            wrong.append(variant)
    assert wrong == []


def test_shared_chain_has_the_box_and_sizes_of_its_runs() -> None:
    """The shared relaxed chain is in the cylinder of every run that reads
    it, and its input relaxes the chain of those runs: the same sizes,
    mass, and wall strengths."""
    text = (LAMMPS / "start" / "minimize.lmp").read_text()
    state = {name: float(value) for name, value in re.findall(
        r"^\s*variable\s+(\w+)\s+equal\s+([\d.]+)\s*$", _code(text),
        re.MULTILINE)}
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


def test_sweep_rows_name_a_neighbor_style_the_inputs_set_up(
        manifest: list[dict[str, str]]) -> None:
    """Every run has ``bin`` or ``multi`` neighbor lists, the two styles
    the inputs set up."""
    assert {row["neigh_style"] for row in manifest} <= {"bin", "multi"}


def test_manifest_is_the_expanded_sweeps(
        manifest: list[dict[str, str]]) -> None:
    """``runs/manifest.csv`` lists each variant's sweep rows once per
    replicate, with the seed ``seed_group + ens``, the row's own settings,
    and, for a setting the sweep does not carry, the value the variant's
    inputs write."""
    expected = []
    for variant in dict.fromkeys(row["variant"] for row in manifest):
        written = _written_in_inputs(variant)
        for row in _sweep(variant):
            first, last = (int(e) for e in row["ens"].split("-"))
            for i in range(first, last + 1):
                name = (
                    f"epss{row['epsilon_small']}epsl{row['epsilon_big']}"
                    f"r{row['r']}al{row['sig2']}nl{row['n_big']}"
                    f"ml{row['m_big']}ns{row['n_small']}ac{row['sig3']}"
                    f"nc{row['n_crowd']}lz{row['lz']}dt{row['run_dt']}"
                    f"bdump{row['bug_dump']}adump{row['all_dump']}"
                    f"ens{i}.ring")
                run = {**written, **row, "variant": variant,
                       "run_name": name, "ens": str(i),
                       "seed": str(int(row["seed_group"]) + i)}
                expected.append({key: run[key] for key in manifest[0]})
    assert manifest == expected


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
