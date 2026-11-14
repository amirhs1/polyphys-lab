"""Type-check the lab with mypy, under the package names it installs.

Each study's ``projects/<study>/python/`` folder installs as
``polyphys_lab.<study>`` through the ``package-dir`` table of
``pyproject.toml``. An editable install provides that mapping with an
import hook, which mypy does not follow, and by path every study's folder
is a module named ``python``. So this script links the folders into a
temporary ``polyphys_lab`` tree and runs mypy on it and on ``tests/``,
with the settings of ``[tool.mypy]`` in ``pyproject.toml``.

Run it from the repository root: ``python tools/typecheck.py``. Extra
arguments are passed to mypy. The exit code is mypy's.
"""
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def link_tree(target: Path) -> Path:
    """Build ``target/polyphys_lab`` from the ``package-dir`` table.

    Parameters
    ----------
    target : Path
        An empty directory to build the tree in.

    Returns
    -------
    Path
        The ``polyphys_lab`` folder in `target`.
    """
    setuptools = tomllib.loads(
        (ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]
    package = target / "polyphys_lab"
    package.mkdir()
    for name, folder in setuptools["package-dir"].items():
        if name == "polyphys_lab":
            for path in (ROOT / folder).iterdir():
                if path.suffix == ".py":
                    (package / path.name).symlink_to(path)
        else:
            (package / name.rsplit(".", 1)[1]).symlink_to(
                ROOT / folder, target_is_directory=True)
    return package


def main(argv: list[str]) -> int:
    """Run mypy on the linked tree and on ``tests/``; return its code."""
    with tempfile.TemporaryDirectory() as tmp:
        package = link_tree(Path(tmp))
        command = [
            sys.executable, "-m", "mypy",
            "--config-file", str(ROOT / "pyproject.toml"),
            str(package), str(ROOT / "tests"), str(ROOT / "tools"),
            *argv,
        ]
        env = {**os.environ, "MYPYPATH": tmp}
        return subprocess.run(command, env=env, cwd=tmp).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
