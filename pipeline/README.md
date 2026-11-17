# pipeline

The general stages that take a study from LAMMPS inputs to its `allInOne`
tables. Stage numbers are execution order.

| Stage         | Does                                                  |
| ------------- | ----------------------------------------------------- |
| `1-simulate/` | generates a sweep, submits it, checks completion      |
| `2-restart/`  | finds incomplete runs, restarts them, merges segments |
| `3-extract/`  | extracts trajectories                                 |
| `4-probe/`    | one job: per-frame observables for a study            |
| `5-reduce/`   | one job: from probes to the `allInOne` tables         |
| `6-archive/`  | compresses, archives, and moves data                  |

`lib/` holds the shell functions the stages share, and `tests/` their
tests. No study name appears under `pipeline/`: a stage takes the study and
the variant as arguments and reads
`projects/<study>/lammps/<variant>/study.conf`.

Each stage's `README.md` is its runbook.
