"""Tests for the LAMMPS inputs, ``study.conf`` files, and manifests of the
studies under ``projects/``.

These are consistency checks with no reference value, run for every study
that has a variant folder: every input is one whole file that reads only
variables it defines or that a pipeline stage writes, each variant's
inputs name the files they pass on, and the manifest is the expansion of
the variants' sweeps under the run names that the inputs give their
output. The checks of a study's own system (its parser, its start
configuration, its particle counts) are in the study's
``python/tests/test_templates.py``.
"""
import csv
import re
import subprocess
from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[1] / "projects"
VARIABLE_USE = re.compile(r"\$\{(\w+)\}|\$(\w)")
VARIABLE_DEFINITION = re.compile(r"^\s*variable\s+(\w+)\s", re.MULTILINE)
READ_DATA = re.compile(r"^\s*read_data\s+(\S+)", re.MULTILINE)
WRITE_DATA = re.compile(r"^\s*write_data\s+(\S+)", re.MULTILINE)


def _variants() -> list[Path]:
    """Return every variant folder: a folder of a study's ``lammps/`` with
    a ``study.conf``."""
    return sorted(p.parent for p in PROJECTS.glob("*/lammps/*/study.conf"))


def _studies() -> list[Path]:
    """Return the folders of the studies that have a variant."""
    return sorted({variant.parents[1] for variant in _variants()})


def _inputs() -> list[Path]:
    """Return every LAMMPS input of every study, those of ``start/`` among
    them."""
    return sorted(PROJECTS.glob("*/lammps/*/*.lmp"))


def _id(path: Path) -> str:
    """Return a test id: the path under ``projects/``, without
    ``lammps/``."""
    parts = path.relative_to(PROJECTS).parts
    return "/".join(part for part in parts if part != "lammps")


def _table(variant: Path, name: str) -> list[list[str]]:
    """Return the rows of the bash array `name` in a variant's
    ``study.conf``, split; a plain variable gives one row, and a variable
    that is not set gives none."""
    script = f'source "$1"; printf "%s\\n" "${{{name}[@]}}"'
    result = subprocess.run(
        ["bash", "-c", script, "_", str(variant / "study.conf")],
        check=True, capture_output=True, text=True)
    return [line.split() for line in result.stdout.splitlines() if line]


def _columns(variant: Path) -> list[str]:
    """Return the column names of a variant's ``SWEEP``: the comment line
    that opens the table."""
    text = (variant / "study.conf").read_text()
    match = re.search(r"^SWEEP=\(\n\s*#\s*(.+)$", text, re.MULTILINE)
    assert match is not None
    return match.group(1).split()


def _sweep(variant: Path) -> list[dict[str, str]]:
    """Return a variant's sweep rows, each as a mapping from column name
    to value."""
    columns = _columns(variant)
    rows = _table(variant, "SWEEP")
    assert all(len(row) == len(columns) for row in rows)
    return [dict(zip(columns, row)) for row in rows]


def _manifest(study: Path) -> list[dict[str, str]]:
    """Return the rows of a study's ``runs/manifest.csv``."""
    with open(study / "runs" / "manifest.csv", newline="") as fh:
        return list(csv.DictReader(fh))


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


def _first_input(variant: Path) -> Path:
    """Return the input of a variant that starts from the start
    configuration: ``minimize.lmp``, or ``production.lmp`` where there is
    none."""
    minimize = variant / "minimize.lmp"
    return minimize if minimize.is_file() else variant / "production.lmp"


def _run_name(variant: Path) -> str:
    """Return the name that a variant's ``production.lmp`` gives a run,
    with its variables not yet substituted: the name of the chain's dump
    file before ``.bug.lammpstrj``, with ``run_name`` written out."""
    text = (variant / "production.lmp").read_text()
    name = _value(
        text, r"^\s*dump\s+\S+\s+bug\s+atom\s+\S+\s+(\S+)\.bug\.lammpstrj")
    run_name = _value(text, r"^\s*variable\s+run_name\s+string\s+(\S+)")
    return name.replace("${run_name}", run_name)


def _written_in_inputs(variant: Path) -> dict[str, str]:
    """Return the settings that a variant's inputs write themselves: the
    manifest columns of this kind that its sweep does not carry."""
    production = (variant / "production.lmp").read_text()
    minimize = _first_input(variant).read_text()
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
def stage_variables() -> dict[str, set[str]]:
    """Return the variables that the restart stages add, by input name."""
    return {"restart.lmp": {"restart_file", "nloop", "last_loop_steps"},
            "continue.lmp": {"restart_file", "nloop"}}


@pytest.mark.parametrize("path", _inputs(), ids=_id)
def test_input_reads_only_supplied_variables(
        path: Path, generator_names: dict[str, str],
        stage_variables: dict[str, set[str]]) -> None:
    """An input reads only variables that it defines, that the generator
    writes from the sweep row of its variant, or that its restart stage
    adds; an input of ``start/`` reads none from a row."""
    text = path.read_text()
    supplied = set(stage_variables.get(path.name, set()))
    if (path.parent / "study.conf").is_file():
        supplied |= {generator_names.get(column, column)
                     for column in _columns(path.parent)}
    assert _used(text) - _defined(text) - supplied == set()


@pytest.mark.parametrize("path", _inputs(), ids=_id)
def test_input_is_one_whole_file(path: Path) -> None:
    """An input includes no other file: what a run does is in one place."""
    assert re.findall(r"^\s*include\s+\S+", _code(path.read_text()),
                      re.MULTILINE) == []


@pytest.mark.parametrize("path", _inputs(), ids=_id)
def test_run_lengths_are_variables(path: Path) -> None:
    """No input fixes a step count, a loop count, or a restart period as a
    number."""
    literal = re.compile(r"\brun\s+\d|^\s*restart\s+\d|\bloop\s+\d",
                         re.MULTILINE)
    assert literal.findall(_code(path.read_text())) == []


@pytest.mark.parametrize("study", _studies(), ids=_id)
def test_variant_folders_are_the_manifest_variants(study: Path) -> None:
    """A study's folders with a ``study.conf`` are the variants that its
    manifest names."""
    folders = {v.name for v in _variants() if v.parents[1] == study}
    assert folders == {row["variant"] for row in _manifest(study)}


@pytest.mark.parametrize("variant", _variants(), ids=_id)
def test_variant_names_itself_and_has_production(variant: Path) -> None:
    """A variant folder holds a ``production.lmp``, and its ``study.conf``
    names the study and the variant by their folders."""
    assert (variant / "production.lmp").is_file()
    assert _table(variant, "STUDY") == [[variant.parents[1].name]]
    assert _table(variant, "VARIANT") == [[variant.name]]


@pytest.mark.parametrize("variant", _variants(), ids=_id)
def test_first_input_reads_the_start_file(variant: Path) -> None:
    """The input of a variant that starts from the start configuration
    reads the file that ``START_DATA`` names, and ``start/`` holds it."""
    [[start]] = _table(variant, "START_DATA")
    assert READ_DATA.findall(_first_input(variant).read_text()) == [start]
    assert (variant.parent / "start" / start).is_file()


@pytest.mark.parametrize("variant", _variants(), ids=_id)
def test_production_reads_what_minimize_writes(variant: Path) -> None:
    """Where a variant relaxes the chain first, its ``production.lmp``
    reads the one data file that its ``minimize.lmp`` writes."""
    minimize = variant / "minimize.lmp"
    if not minimize.is_file():
        pytest.skip("the variant has no minimize.lmp")
    written = WRITE_DATA.findall(minimize.read_text())
    assert len(written) == 1
    assert READ_DATA.findall(
        (variant / "production.lmp").read_text()) == written


@pytest.mark.parametrize("variant", _variants(), ids=_id)
def test_shared_chain_is_what_production_reads(variant: Path) -> None:
    """A variant with a sweep row whose ``relax_steps`` is ``shared`` names
    a ``RELAXED_DATA`` that ``start/`` holds, that ``start/minimize.lmp``
    writes from the start file, and that its ``production.lmp`` reads; a
    variant without such a row names none."""
    shared = [row for row in _sweep(variant)
              if row.get("relax_steps") == "shared"]
    relaxed = _table(variant, "RELAXED_DATA")
    if not shared:
        assert relaxed == []
        return
    [[start]] = _table(variant, "START_DATA")
    start_input = (variant.parent / "start" / "minimize.lmp").read_text()
    assert len(relaxed) == 1
    assert READ_DATA.findall(
        (variant / "production.lmp").read_text()) == relaxed[0]
    assert WRITE_DATA.findall(start_input) == relaxed[0]
    assert READ_DATA.findall(start_input) == [start]
    assert (variant.parent / "start" / relaxed[0][0]).is_file()


@pytest.mark.parametrize("study", _studies(), ids=_id)
def test_manifest_names_a_neighbor_style_the_inputs_set_up(
        study: Path) -> None:
    """Every run has ``bin`` or ``multi`` neighbor lists, the two styles
    the inputs set up."""
    assert {row["neigh_style"] for row in _manifest(study)} <= {
        "bin", "multi"}


@pytest.mark.parametrize("study", _studies(), ids=_id)
def test_manifest_is_the_expanded_sweeps(
        study: Path, generator_names: dict[str, str]) -> None:
    """A manifest lists each variant's sweep rows once per replicate, under
    the name that ``production.lmp`` gives the run, with the seed
    ``seed_group + ens``, the row's own settings, and, for a setting the
    sweep does not carry, the value the variant's inputs write."""
    manifest = _manifest(study)
    expected = []
    for name in dict.fromkeys(row["variant"] for row in manifest):
        variant = study / "lammps" / name
        written = _written_in_inputs(variant)
        template = _run_name(variant)
        for row in _sweep(variant):
            variables = {generator_names.get(column, column): value
                         for column, value in row.items()}
            first, last = (int(e) for e in row["ens"].split("-"))
            for i in range(first, last + 1):
                variables["i"] = str(i)
                run_name = re.sub(
                    r"\$\{(\w+)\}", lambda m: variables[m.group(1)],
                    template)
                run = {**written, **row, "variant": name,
                       "run_name": run_name, "ens": str(i),
                       "seed": str(int(row["seed_group"]) + i)}
                expected.append({key: run[key] for key in manifest[0]})
    assert manifest == expected


@pytest.mark.parametrize("study", _studies(), ids=_id)
def test_manifest_identifies_each_run_once(study: Path) -> None:
    """No two manifest rows share a variant and a run name."""
    keys = [(row["variant"], row["run_name"]) for row in _manifest(study)]
    assert len(keys) == len(set(keys))
