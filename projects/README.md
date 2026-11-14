# projects

One folder per study. "Project" and "study" name the same thing.

```text
<study>/
  README.md         the paper, the state points, and what ran where
  python/           parser.py, spec.py, driver.py, corrections.py, tests/
  lammps/           README.md, input templates, restart/, start/
  slurm/            study.conf and thin wrappers that call pipeline/
  notebooks/        the study's figure notebooks
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

No study is here yet.
