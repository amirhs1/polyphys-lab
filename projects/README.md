# projects

One folder per study. "Project" and "study" name the same thing.

```text
<study>/
  README.md         the paper, the state points, and what ran where
  python/           parser.py, spec.py, driver.py, corrections.py, tests/
  lammps/           README.md, input templates, restart/, start/
  slurm/            study.conf and thin wrappers that call pipeline/
  notebooks/        the study's notebooks
  runs/manifest.csv one row per run name
```

- `python/` installs as `polyphys_lab.<study>`; `pyproject.toml` lists it.
- `lammps/README.md` says what each template simulates and how its
  variants differ. `lammps/start/` holds the start configuration and the
  script that builds it.
- `slurm/study.conf` holds the sweep values and the resource table that
  the stages in `pipeline/` read.
- `runs/manifest.csv` lists every run of the study by name.

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
