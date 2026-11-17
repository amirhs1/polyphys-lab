# projects

One folder per study. "Project" and "study" name the same thing.

```text
<study>/
  README.md         the paper, the runs, and the LAMMPS inputs
  python/           parser.py, spec.py, driver.py, corrections.py, tests/
  lammps/           one folder per variant, and start/
  slurm/            thin wrappers that call pipeline/
  notebooks/        the study's notebooks
  runs/manifest.csv one row per run
```

- `python/` installs as `polyphys_lab.<study>`; `pyproject.toml` lists it.
- `README.md` is the study's one README; it also says what the LAMMPS
  inputs simulate.
- `lammps/<variant>/` holds the inputs of one set of runs, each of them
  one whole file with no `include`, and the variant's `study.conf`: its
  LAMMPS version and modules, its sweep, and the resource table that the
  stages in `pipeline/` read. A study whose runs all share their physics
  and numerics has one variant.
- `lammps/start/` holds the start configuration and the script that
  builds it.
- `runs/manifest.csv` lists every run of the study by variant and name.

`tests/test_layout.py` checks that every study folder has these parts.

| Folder            | Study          | Package                       |
| ----------------- | -------------- | ----------------------------- |
| `trans_foci_cyl/` | `TransFociCyl` | `polyphys_lab.trans_foci_cyl` |
| `trans_foci_cub/` | `TransFociCub` | `polyphys_lab.trans_foci_cub` |
| `hns_cub/`        | `HnsCub`       | `polyphys_lab.hns_cub`        |
| `hns_cyl/`        | `HnsCyl`       | `polyphys_lab.hns_cyl`        |

`tests/test_studies.py`, at the repository root, checks every study's
specs against its parser and against the research code's registry.

The private-data tests in each `python/tests/test_parser.py` run only
when `POLYPHYS_DATA_DIR` names a folder of processed artifacts, and are
skipped otherwise.
