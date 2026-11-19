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
  inputs, parsers, and specs. `projects/hns_cub/` holds its parser and
  specs only.
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
    data/probe/         trimmed real frames of 14 wholes of the three studies
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

## AI assistance

This repository is developed with the help of AI coding assistants. Every
change is reviewed and merged by the maintainer, who is accountable for the
result; no AI system is an author of it. See [`AI-POLICY.md`](AI-POLICY.md)
for the full policy, including what is expected of AI-assisted contributions.

Each part has a tier, set by whether I can evaluate AI output there. The table
records the checks or human review applied to each part:

- **Instrumented** — I could write it myself. AI is used for review,
  refactoring, and alternative implementations, not first drafts of core logic.
- **Supervised** — AI drafts; I read every line and set the acceptance criteria
  and test values.
- **Delegated** — AI generates; I can't fully evaluate it. It is covered by
  tests, kept isolated and low-risk, and not presented as my work.

| Part                                                            | Tier       | Checks or human review                                                                                               |
| --------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------- |
| `projects/<study>/lammps/`, `projects/<study>/runs/`            | Supervised | CI: the template checks; each input compared with the published runs, as its study README says; every line reviewed  |
| `projects/<study>/python/`, `tests/`, `tools/`, `polyphys_lab/` | Supervised | CI: flake8, mypy, pytest on Python 3.14, and the tests against PolyPhys `main`; maintainer review of every line      |
| `pipeline/`, `projects/<study>/slurm/`, `config/`               | Supervised | CI: ShellCheck; no script yet, and nothing run on a cluster; maintainer review of every line                         |
| `notebooks/`, `projects/<study>/notebooks/`                     | Supervised | No notebook yet; maintainer review of every line                                                                     |
| `.github/workflows/`, `pyproject.toml`                          | Supervised | CI on every pull request; maintainer review of every line                                                            |

Nothing that handles security, credentials, private data, or published results,
or that can block a merge, is Delegated. Where a tier is unclear, I treat the
part as Supervised. Tiers last reviewed: 2026-11-19.

Instructions for AI agents: [`AGENTS.md`](AGENTS.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the setup, the checks, and the
names of branches, commits, and labels, and [`SECURITY.md`](SECURITY.md) for
reporting a vulnerability.

## License

MIT; see `LICENSE`.
