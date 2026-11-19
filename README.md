# polyphys-lab

The study records and the cluster pipeline that go with
[PolyPhys](https://github.com/amirhs1/PolyPhys), a Python package for managing
and analyzing large-scale polymer molecular-dynamics simulations.

PolyPhys is the library. This repository holds what a study needs around it:
the LAMMPS input templates, the SLURM jobs that run and process a parameter
sweep, each study's parser and specs, and the notebooks that draw its figures.

This repository depends on a released `polyphys`. PolyPhys does not depend on
this repository.

## Status

This repository is being built, and nothing in it has been run on a cluster
from here yet.

- `projects/trans_foci_cub/` and `projects/trans_foci_cyl/` hold their LAMMPS
  inputs, parsers, and specs. `projects/hns_cub/` and `projects/hns_cyl/`
  hold their parsers and specs only.
- Each stage in `pipeline/` has a `README.md` and no script yet.
- No study has its `slurm/` or `notebooks/` folder yet.

Read the inputs as a record of what the published runs simulated, not as a
tested workflow.

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
      README.md         the paper, the runs, and the LAMMPS inputs
      python/           parser.py, spec.py, driver.py, corrections.py, tests/
      lammps/
        <variant>/      the inputs and the study.conf of one set of runs
        start/          the start configuration
      slurm/            thin wrappers that call pipeline/
      notebooks/        the study's notebooks
      runs/manifest.csv one row per run
  notebooks/            plot settings and notebooks shared by the studies
  tests/                the layout checks and the cross-study spec and
                        template checks
    probe/, analyze/,   the studies' specs run on real frames, and the
    viz/                comparisons with the research code's output
    data/probe/         trimmed real frames of 22 wholes of the four studies
```

A stage in `pipeline/` takes the study and the variant as arguments and reads
the variant's `study.conf`; it never names a study itself.

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

The tests marked `private_data` compare with the maintainer's processed
data and run only when `POLYPHYS_DATA_DIR` names its folder; they are
skipped otherwise. A CI job also runs the tests against PolyPhys `main`,
without blocking a merge.

## Running on a cluster

Copy `config/cluster.conf.example` to `config/cluster.conf` and fill it in.
`cluster.conf` is ignored by git: account names, addresses, and storage paths
live only there. Each stage has a `README.md` that is its runbook.

## License

MIT; see `LICENSE`.
