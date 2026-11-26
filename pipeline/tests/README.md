# tests

The shell test harness of the pipeline, in pure bash. It runs on small
folders that each test builds, never on a cluster, and needs no SLURM. CI
runs it in the "Lint shell" job.

```bash
bash pipeline/tests/run_tests.sh                   # every test
bash pipeline/tests/run_tests.sh -k tmp            # tests whose name holds "tmp"
bash pipeline/tests/run_tests.sh -v                # also show passing tests' output
bash pipeline/tests/run_tests.sh --root DIR        # test a copy of the lab at DIR
bash pipeline/tests/run_tests.sh pipeline/tests/test_common.sh
```

It needs bash 4.4 or later. On macOS, `/bin/bash` is 3.2: put Homebrew's
bash first on `PATH`, and the harness refuses the old one with a hint.
ShellCheck is needed for one static test, which is skipped without it.

| File               | Tests                                                                                         |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `test_common.sh`   | each function of `pipeline/lib/common.sh`                                                     |
| `test_static.sh`   | every shell file parses and is ShellCheck-clean; no in-place edit, identity line, or address; the stage scripts' header |
| `test_harness.sh`  | the harness itself: it reports a failure, and it isolates each test                           |

Each stage's `README.md` lists that stage's own tests.

## Isolation

- Each test function runs in its own bash process, so `set -e` stays in
  force inside it, and in its own `mktemp -d` sandbox, removed afterwards.
- `HOME` points into the sandbox, and the working folder is nested four
  levels down, so a script that climbs with `cd ..` stays inside.
- `sbatch`, `srun`, `scancel`, `squeue`, `sacct`, `rsync`, `module`, and
  `parallel` are stubs first on `PATH` in every test. Each logs its folder
  and arguments; none reaches a scheduler or copies data.
- `LAB_CLUSTER_CONF`, `LAB_PROJECTS_DIR`, `LAB_DRY_RUN`, and every
  `SLURM_*` variable are cleared, so a run on a cluster node inherits none.
- No test reads or writes `config/cluster.conf`, cluster storage, or
  simulation data. A test may read a tracked file of the lab, such as each
  `study.conf`, and never writes one.

## Adding a test

1. Put `test_<unit>_<behavior>() { ... }` in a `test_<area>.sh` file
   here. The file is sourced, not run: no shebang, and its first line is
   `# shellcheck shell=bash`.
2. Above the function, one comment line in the present tense states the
   behavior it protects.
3. Build the fixtures in the working folder (`W`) or the sandbox (`T`).
   Run code with `run_script SCRIPT` or `run_with_lib CODE`, which sources
   the library under test first, then assert. The helpers are in
   `lib/helpers.sh`: `assert_status`, `assert_content`, `assert_match`,
   `assert_no_match`, `assert_empty`, `assert_exists`, `assert_missing`,
   `assert_not_called`, `stub`, `stub_calls`, `snapshot`, `make_study`,
   `skip`, and `fail`.
4. A made-up study in a fixture gets a name that contains no study folder
   name; `tests/test_layout.py` checks every file under `pipeline/`.
5. Show that the test fails. Copy the lab outside the working tree, plant
   the fault the test guards against in the copy, and run
   `bash pipeline/tests/run_tests.sh --root <copy>`. Never plant a fault in
   a working tree.

Exit status: 0 when no test failed (a skip, exit 77, is not a failure), 1
when one did, 2 on misuse.
