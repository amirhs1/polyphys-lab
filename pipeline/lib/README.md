# lib

`common.sh` holds the shell functions that every stage and every study's
`slurm/` wrapper shares: reading `config/cluster.conf`, finding a study's
`study.conf`, guarding `SLURM_TMPDIR`, editing a file with a backup,
submitting, and reporting real exit codes and the reason a job failed.
`pipeline/tests/test_common.sh` tests each function.

## Using it

A stage script starts:

```bash
#!/bin/bash
set -euo pipefail
# shellcheck source=../lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
```

- The library is sourced, never run; run as a command, it exits 2.
- It needs bash 4.4 or later, and returns 2 under an older bash. The check
  is written so that macOS's `/bin/bash` 3.2 reaches it.
- Sourcing it sets no shell option and installs no trap; the stage sets
  `set -euo pipefail`. A second `source` changes nothing.
- Every name it defines starts with `lab_` or `LAB_`. `LAB_ROOT` is the
  lab's root, found from the library's own path.
- A function that yields a value sets a variable whose name the caller
  gives, such as `lab_tmp_path dest x`. `exit` inside `$(...)` would end
  only the subshell, and the caller would go on with an empty value.

## Exit codes

| Code    | Means                                                             |
| ------- | ----------------------------------------------------------------- |
| 0       | success                                                           |
| 1       | a step failed                                                     |
| 2       | refused: a usage error, a missing or invalid setting, or a guard  |
| 128 + N | ended by signal N: 130 for INT, 143 for TERM                      |

A guard or a loader exits through `lab_die` when it fails, since the stage
cannot go on without it. An operation returns its code and leaves the
decision to the caller. `lab_run`, `lab_sbatch`, and `lab_rewrite` return
the code of the command they ran.

## Functions

### Logging

| Function                         | Does                                                       |
| -------------------------------- | ---------------------------------------------------------- |
| `lab_log MESSAGE...`             | one line on stderr: `<UTC time> <script> info: <message>`  |
| `lab_warn MESSAGE...`            | the same, at level `warn`                                  |
| `lab_die [-c CODE] MESSAGE...`   | the same, at level `error`, then exit CODE (default 1)     |

stdout stays free for a stage's own output.

### Settings and studies

| Function                               | Does                                                                                                                                                  |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lab_load_cluster_conf`                | sources `LAB_CLUSTER_CONF`, else `config/cluster.conf`; exits 2 when the file is missing or fails `bash -n`, so a broken file loads nothing           |
| `lab_require VAR...`                   | exits 2, naming every VAR that is unset, empty, or still `CHANGE_ME`, in one message                                                                  |
| `lab_check_name KIND VALUE`            | exits 2 unless VALUE matches `^[a-z0-9][a-z0-9_]*$`                                                                                                   |
| `lab_study_conf VAR STUDY VARIANT`     | sets VAR to `<projects>/<STUDY>/lammps/<VARIANT>/study.conf`, where `<projects>` is `LAB_PROJECTS_DIR`, else the lab's `projects/`; exits 2 and lists the studies or the variants that exist when one is missing |
| `lab_load_study STUDY VARIANT`         | sources that `study.conf`, and exits 2 unless its `STUDY` and `VARIANT` are the arguments                                                             |

A study kept in another repository sets `LAB_PROJECTS_DIR` to that
repository's `projects/` before it calls a stage. `cluster.conf` and
`study.conf` are sourced inside a function, so they use plain assignments:
a `declare` in them would make a local that disappears on return.

### `SLURM_TMPDIR`

| Function                        | Does                                                                                                           |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `lab_tmpdir VAR`                | sets VAR to `SLURM_TMPDIR`; exits 2 when it is unset, empty, `/`, not a folder, or not writable                |
| `lab_tmp_path VAR RELATIVE`     | sets VAR to `SLURM_TMPDIR/RELATIVE`; exits 2 as above, or when RELATIVE is empty, absolute, or has a `.` or `..` component |
| `lab_rm_tmp RELATIVE`           | removes `SLURM_TMPDIR/RELATIVE` after the same checks, and never the folder itself; returns 2 when a check fails |

No stage script and no study wrapper names `SLURM_TMPDIR`; every use goes
through these three, and `test_static.sh` checks it. Outside a job there is
no fallback folder.

### In-place edits

| Function                             | Does                                                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `lab_backup FILE`                    | copies FILE to `FILE.orig`, with its mode and time; returns 1 and changes nothing when `FILE.orig` exists, so the first original stays |
| `lab_rewrite FILE COMMAND [ARGS...]` | backs FILE up, runs COMMAND with `FILE.orig` on stdin, and replaces FILE with its output only when COMMAND exits 0                     |

No stage script, study wrapper, or library line runs `sed -i` or
`perl -i`. Since `lab_rewrite` keeps the first original, a file takes one
rewrite; several edits go into one command, such as `sed -e ... -e ...`.

### Jobs, exit codes, and what happened

| Function                                          | Does                                                                                                                                                         |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `lab_job_begin LABEL`                             | writes the begin block, and traps `EXIT`, `TERM`, and `INT`, so that the job line carries the script's real code                                            |
| `lab_run [-o FILE] [-f FILE]... LABEL COMMAND...` | runs COMMAND, keeps its stderr in `LABEL.stderr` and copies it to stderr, writes the step line, and on failure the summary; with `-o`, stdout goes to FILE |
| `lab_failure_summary LABEL CODE [FILE...]`        | the summary, from the signal and from the lines of each FILE that match `LAB_FAILURE_PATTERNS`                                                              |
| `lab_last_status FILE`                            | prints the code of FILE's last job line, `none`, or `legacy`                                                                                                 |
| `lab_job_state JOBID`                             | prints each step of the job from SLURM's accounting (`sacct`): step, state, exit code, node list, elapsed time, maximum resident memory, requested memory      |

A job's output, `slurm-<jobid>.out`, then holds:

```text
Lab job begin at: <UTC time>
  label, job id, array task id, job name, node list, nodes, tasks,
  CPUs per task, memory per CPU, host, working folder, bash, lab commit,
  modules
...
Step <label> finished with exit code <code> at: <UTC time>
Failure summary for <label>:          (only after a failure)
  signal: TERM                        (only for 128 + N)
  log.lammps:812:ERROR on proc 3: ...
...
Program finished with exit code <code> at: <UTC time>
```

- The summary lists the matching lines with their file and line number,
  at most `LAB_FAILURE_MAX_LINES` (40). With no match, it shows the last
  `LAB_FAILURE_TAIL_LINES` (20) lines of the step's stderr. With nothing
  to read, it says `no reason found in:` and the files it read; it never
  guesses.
- `LAB_FAILURE_PATTERNS` holds LAMMPS's `ERROR` and `ERROR on proc N`
  lines, which name the MPI rank; a Python traceback and its exception
  line; and the `srun` and `slurmstepd` messages that name a node, a
  task, a time limit, memory exhaustion, a cancellation, or a node
  failure. Each allows the `N: ` prefix of `srun --label`. The SLURM
  patterns are not yet checked against real output.
- `lab_last_status` says `legacy` for a file that has a job line but no
  begin block, because older scripts wrote the same wording with a code
  that was always 0.
- A job whose node fails, or that is killed with SIGKILL, runs no trap and
  writes no job line. A missing line is never read as success; the reason
  is then in SLURM's accounting, which `lab_job_state` reads after the job.
  The harness stubs `sacct`.

### Submitting

`lab_sbatch [SBATCH ARGS...] SCRIPT [ARGS...]` calls `sbatch` with these
arguments unchanged and returns its code. With `LAB_DRY_RUN=1` it only
prints the command. It refuses, with code 2, any argument that sets the
account (`-A`, `--account`) or a mail address (`--mail-user`): the account
comes from `SBATCH_ACCOUNT` on the cluster.
