"""Checks of the repository's own layout."""
import importlib
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUDY_CODE_PARTS = ("README.md", "python/__init__.py", "python/tests")
STUDY_RUN_PARTS = (
    "lammps/README.md",
    "slurm/study.conf",
    "notebooks",
    "runs/manifest.csv",
)


def _studies() -> list[Path]:
    """Return the study folders under ``projects/``."""
    return sorted(p for p in (ROOT / "projects").iterdir() if p.is_dir())


def test_package_imports() -> None:
    """The package root that the studies install under imports."""
    assert importlib.import_module("polyphys_lab").__doc__


def _missing(parts: tuple[str, ...]) -> list[str]:
    """Return ``<study>/<part>`` for each part a study folder lacks."""
    return [
        f"{study.name}/{part}"
        for study in _studies()
        for part in parts
        if not (study / part).exists()
    ]


def test_every_study_has_its_code() -> None:
    """Each study folder holds its README and its Python package."""
    assert _missing(STUDY_CODE_PARTS) == []


@pytest.mark.xfail(
    strict=True,
    reason="the LAMMPS, SLURM, notebook, and run parts are not written yet")
def test_every_study_has_its_run_parts() -> None:
    """Each study folder holds its LAMMPS, SLURM, notebook, and run parts."""
    assert _missing(STUDY_RUN_PARTS) == []


def test_every_study_is_a_listed_package() -> None:
    """``pyproject.toml`` maps each study's ``python/`` to a subpackage."""
    setuptools = tomllib.loads(
        (ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]
    expected = {
        f"polyphys_lab.{study.name}": f"projects/{study.name}/python"
        for study in _studies()
    }
    mapped = {
        name: folder
        for name, folder in setuptools["package-dir"].items()
        if name != "polyphys_lab"
    }
    assert mapped == expected
    assert set(setuptools["packages"]) == {"polyphys_lab", *expected}


def test_no_study_name_in_pipeline() -> None:
    """No file under ``pipeline/`` names a study."""
    names = [study.name for study in _studies()]
    hits = [
        f"{path.relative_to(ROOT)}: {name}"
        for path in (ROOT / "pipeline").rglob("*")
        if path.is_file()
        for name in names
        if name in path.read_text(errors="ignore")
    ]
    assert hits == []
