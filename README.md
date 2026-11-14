# polyphys-lab

The study records and the cluster pipeline that go with
[PolyPhys](https://github.com/amirhs1/PolyPhys), a Python package for managing
and analyzing large-scale polymer molecular-dynamics simulations.

PolyPhys is the library. This repository holds what a study needs around it:
the LAMMPS input templates, the SLURM jobs that run and process a parameter
sweep, each study's parser and specs, and the notebooks that draw its figures.

This repository depends on a released `polyphys`. PolyPhys does not depend on
this repository.

## Layout

```text
polyphys-lab/
  pyproject.toml        pins a released polyphys
  polyphys_lab/         the package root
  config/               cluster.conf.example: the one place for site settings
  pipeline/             general stages; no study name appears in here
    lib/                shared shell functions
    1-simulate/         generate a sweep, submit it, check completion
    2-restart/          find incomplete runs, restart them, merge segments
    3-extract/          extract trajectories
    4-probe/            one job: per-frame observables for a study
    5-reduce/           one job: from probes to the allInOne tables
    6-archive/          compress, archive, and move data
    tests/              shell tests of the stages
  projects/             one folder per study
    <study>/
      README.md         the paper, the state points, and what ran where
      python/           parser.py, spec.py, driver.py, corrections.py, tests/
      lammps/           input templates, restart inputs, start configurations
      slurm/            study.conf and thin wrappers that call pipeline/
      notebooks/        the study's notebooks
      runs/manifest.csv one row per run name
  notebooks/            plot settings and notebooks shared by the studies
  tests/                checks of the repository's own layout
```

A stage in `pipeline/` takes the study as an argument and reads the study's
`slurm/study.conf`; it never names a study itself.

## Install

In a Python environment of your own (3.11 or later):

```bash
python -m pip install -e '.[dev]'
```

Each study's `python/` folder is then importable as `polyphys_lab.<study>`, for
example `polyphys_lab.trans_foci_cub.spec`.

## Checks

```bash
python -m pytest
python -m flake8 polyphys_lab projects tests tools
python tools/typecheck.py
git ls-files '*.sh' | xargs shellcheck
```

## Running on a cluster

Copy `config/cluster.conf.example` to `config/cluster.conf` and fill it in.
`cluster.conf` is ignored by git: account names, addresses, and storage paths
live only there. Each stage has a `README.md` that is its runbook.
