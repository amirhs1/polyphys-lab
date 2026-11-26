# shellcheck shell=bash
# shellcheck disable=SC2016  # code for run_with_lib runs in a child bash, so it is single-quoted
# Tests of pipeline/lib/common.sh. Each expected value is the library's
# contract (pipeline/lib/README.md), the fixture the test builds, or the
# behavior of bash or Python, as each test's comment says.

# --- Form ---------------------------------------------------------------

# Running the library as a command refuses with code 2 and one line.
test_lib_run_as_command_refuses() {
    run_script "${LAB_LIB}"
    assert_status 2
    assert_empty "${T}/out"
    [[ "$(wc -l <"${T}/err" | tr -d ' ')" -eq 1 ]] || fail "expected one line on stderr"
}

# Sourcing the library a second time keeps a caller's override of its
# settings.
test_lib_second_source_keeps_overrides() {
    run_with_lib <<'EOF'
LAB_FAILURE_MAX_LINES=5
source "${LAB_LIB}"
printf '%s\n' "${LAB_FAILURE_MAX_LINES}"
EOF
    assert_status 0
    assert_content "${T}/out" 5
}

# Sourcing the library changes no shell option and installs no trap.
test_lib_source_changes_no_option_or_trap() {
    write_case "$(
        cat <<'EOF'
set -o >"${T}/o1"; shopt >"${T}/s1"; trap -p >"${T}/t1"
source "${LAB_LIB}"
set -o >"${T}/o2"; shopt >"${T}/s2"; trap -p >"${T}/t2"
EOF
    )"
    run_script "${T}/case.sh"
    assert_status 0
    local f
    for f in o s t; do
        cmp -s "${T}/${f}1" "${T}/${f}2" || fail "${f}: changed by sourcing"
    done
}

# A bash below 4.4 is refused with code 2, naming the floor.
test_lib_old_bash_is_refused() {
    [[ -x /bin/bash ]] || skip "no /bin/bash"
    local major minor
    read -r major minor < <(/bin/bash -c 'echo "${BASH_VERSINFO[0]} ${BASH_VERSINFO[1]}"')
    if ((major > 4 || (major == 4 && minor >= 4))); then
        skip "/bin/bash is ${major}.${minor}, not older than the floor"
    fi
    STATUS=0
    /bin/bash -c 'source "$1"' _ "${LAB_LIB}" >"${T}/out" 2>"${T}/err" || STATUS=$?
    assert_status 2
    assert_match "${T}/err" '4\.4 or later'
}

# LAB_ROOT is the root of the lab under test, from any working folder.
test_lib_root_is_the_lab_root() {
    run_with_lib 'printf "%s\n" "${LAB_ROOT}"'
    assert_status 0
    assert_content "${T}/out" "${LAB_TEST_ROOT}"
}

# --- Logging ------------------------------------------------------------

# Log lines go to stderr in the fixed form, and stdout stays empty.
test_log_lines_go_to_stderr_in_form() {
    run_with_lib 'lab_log hello there; lab_warn careful'
    assert_status 0
    assert_empty "${T}/out"
    local stamp='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z case\.sh'
    assert_match "${T}/err" "${stamp} info: hello there$"
    assert_match "${T}/err" "${stamp} warn: careful$"
}

# lab_die exits with its code, 1 by default.
test_die_exits_with_its_code() {
    run_with_lib 'lab_die broken; echo reached'
    assert_status 1
    assert_empty "${T}/out"
    assert_match "${T}/err" 'error: broken$'
    run_with_lib 'lab_die -c 2 refused; echo reached'
    assert_status 2
    assert_empty "${T}/out"
}

# --- Site settings ------------------------------------------------------

# A missing cluster.conf is refused, naming its path and the example.
test_cluster_conf_missing_is_refused() {
    run_with_lib 'LAB_CLUSTER_CONF="${T}/absent.conf"; lab_load_cluster_conf; echo reached'
    assert_status 2
    assert_empty "${T}/out"
    assert_match "${T}/err" 'absent\.conf'
    assert_match "${T}/err" 'cluster\.conf\.example'
}

# LAB_CLUSTER_CONF names the file that is read.
test_cluster_conf_override_is_read() {
    printf 'SCRATCH_DIR="%s/scratch"\n' "${T}" >"${T}/site.conf"
    run_with_lib 'LAB_CLUSTER_CONF="${T}/site.conf"; lab_load_cluster_conf; printf "%s\n" "${SCRATCH_DIR}"'
    assert_status 0
    assert_content "${T}/out" "${T}/scratch"
}

# A cluster.conf with a syntax error loads nothing.
test_cluster_conf_syntax_error_loads_nothing() {
    printf 'GOOD=1\nBAD="unclosed\n' >"${T}/site.conf"
    run_with_lib <<'EOF'
trap 'printf "GOOD=%s\n" "${GOOD-unset}"' EXIT
LAB_CLUSTER_CONF="${T}/site.conf"
lab_load_cluster_conf
EOF
    assert_status 2
    assert_content "${T}/out" "GOOD=unset"
}

# lab_require names every unset, empty, or placeholder variable at once.
test_require_names_every_fault() {
    run_with_lib <<'EOF'
A_EMPTY=""; A_PLACEHOLDER="${HOME}/CHANGE_ME"; A_OK=1
lab_require A_UNSET A_EMPTY A_PLACEHOLDER A_OK
echo reached
EOF
    assert_status 2
    assert_empty "${T}/out"
    assert_match "${T}/err" 'A_UNSET \(unset\)'
    assert_match "${T}/err" 'A_EMPTY \(empty\)'
    assert_match "${T}/err" 'A_PLACEHOLDER \(still CHANGE_ME\)'
    assert_no_match "${T}/err" 'A_OK'
    [[ "$(wc -l <"${T}/err" | tr -d ' ')" -eq 1 ]] || fail "expected one message"
}

# --- Finding a study ----------------------------------------------------

# Every study.conf of the lab loads, and names its own study and variant.
test_every_study_conf_of_the_lab_loads() {
    local conf variant study n=0
    for conf in "${LAB_TEST_ROOT}"/projects/*/lammps/*/study.conf; do
        [[ -f "${conf}" ]] || continue
        variant="$(basename "$(dirname "${conf}")")"
        study="$(basename "$(dirname "$(dirname "$(dirname "${conf}")")")")"
        run_with_lib "lab_load_study ${study} ${variant}; printf '%s %s\n' \"\${STUDY}\" \"\${VARIANT}\""
        assert_status 0 "${study}/${variant}"
        assert_content "${T}/out" "${study} ${variant}"
        n=$((n + 1))
    done
    ((n > 0)) || skip "no study.conf in the lab under test"
}

# A bad study or variant name is refused before any path is built.
test_study_conf_refuses_bad_names() {
    make_study "${T}/projects" alpha one
    local name
    for name in '' 'a/b' '..' 'Alpha' '-x'; do
        run_with_lib "trap 'printf \"%s\n\" \"\${conf-unset}\"' EXIT
LAB_PROJECTS_DIR=\"\${T}/projects\"
lab_study_conf conf '${name}' one"
        assert_status 2 "study '${name}'"
        assert_content "${T}/out" unset "study '${name}'"
        run_with_lib "LAB_PROJECTS_DIR=\"\${T}/projects\"; lab_study_conf conf alpha '${name}'"
        assert_status 2 "variant '${name}'"
    done
}

# A missing study lists the studies, and a missing variant the variants.
test_study_conf_lists_what_exists() {
    make_study "${T}/projects" alpha one
    make_study "${T}/projects" alpha two
    make_study "${T}/projects" beta one
    run_with_lib 'LAB_PROJECTS_DIR="${T}/projects"; lab_study_conf conf gamma one'
    assert_status 2
    assert_match "${T}/err" 'studies: alpha, beta$'
    run_with_lib 'LAB_PROJECTS_DIR="${T}/projects"; lab_study_conf conf alpha three'
    assert_status 2
    assert_match "${T}/err" 'variants: one, two$'
}

# LAB_PROJECTS_DIR finds a study in a projects folder outside the lab.
test_study_conf_reads_another_root() {
    make_study "${T}/other/projects" toy_study toy_variant
    run_with_lib 'LAB_PROJECTS_DIR="${T}/other/projects"; lab_study_conf conf toy_study toy_variant; printf "%s\n" "${conf}"'
    assert_status 0
    assert_content "${T}/out" "${T}/other/projects/toy_study/lammps/toy_variant/study.conf"
}

# A study.conf that names another study or variant is refused.
test_load_study_refuses_a_conf_naming_another() {
    make_study "${T}/projects" alpha one alpha two
    run_with_lib 'LAB_PROJECTS_DIR="${T}/projects"; lab_load_study alpha one; echo reached'
    assert_status 2
    assert_empty "${T}/out"
    assert_match "${T}/err" "VARIANT='two'"
}

# --- SLURM_TMPDIR -------------------------------------------------------

# lab_tmpdir refuses an unset, empty, root, missing, or read-only folder,
# each for its own reason, and accepts a writable one.
test_tmpdir_refuses_unusable_folders() {
    mkdir -p "${T}/node" "${T}/readonly"
    chmod 555 "${T}/readonly"
    local case setting reason
    for case in 'unset SLURM_TMPDIR|is not set' 'SLURM_TMPDIR=""|is empty' \
        'SLURM_TMPDIR=/|is the root folder' 'SLURM_TMPDIR=//|is the root folder' \
        'SLURM_TMPDIR="${T}/missing"|is not a folder' \
        'SLURM_TMPDIR="${T}/readonly"|is not writable'; do
        setting="${case%|*}"
        reason="${case#*|}"
        run_with_lib "${setting}; lab_tmpdir dir; echo reached"
        assert_status 2 "${setting}"
        assert_empty "${T}/out" "${setting}"
        assert_match "${T}/err" "SLURM_TMPDIR ${reason}" "${setting}"
    done
    run_with_lib 'SLURM_TMPDIR="${T}/node"; lab_tmpdir dir; printf "%s\n" "${dir}"'
    assert_status 0
    assert_content "${T}/out" "${T}/node"
}

# With SLURM_TMPDIR unset, the copy into it stops the job before cp runs.
test_tmp_path_unset_stops_the_copy() {
    stub cp
    mkdir -p x
    run_with_lib <<'EOF'
set -euo pipefail
unset SLURM_TMPDIR
lab_tmp_path dest x
cp -R x "${dest}"
EOF
    assert_status 2
    assert_not_called cp
}

# lab_tmp_path refuses an empty, absolute, "." or ".." path, and joins a
# plain one.
test_tmp_path_refuses_paths_outside() {
    mkdir -p "${T}/node"
    local rel
    for rel in '' '/x' 'a/../..' '..' '.' 'a/./b'; do
        run_with_lib "SLURM_TMPDIR=\"\${T}/node\"; lab_tmp_path p '${rel}'; echo reached"
        assert_status 2 "'${rel}'"
        assert_empty "${T}/out" "'${rel}'"
    done
    run_with_lib 'SLURM_TMPDIR="${T}/node"; lab_tmp_path p a/b; printf "%s\n" "${p}"'
    assert_status 0
    assert_content "${T}/out" "${T}/node/a/b"
}

# lab_rm_tmp removes only a path inside the tmpdir, never the tmpdir.
test_rm_tmp_removes_only_inside() {
    mkdir -p "${T}/tmp/node/job" "${T}/tmp/node/keep"
    : >"${T}/tmp/node/job/f"
    : >"${T}/tmp/sentinel"
    run_with_lib 'SLURM_TMPDIR="${T}/tmp/node"; lab_rm_tmp job'
    assert_status 0
    assert_missing "${T}/tmp/node/job"
    assert_exists "${T}/tmp/node/keep"
    assert_exists "${T}/tmp/sentinel"
    local rel
    for rel in '' '../sentinel' '.' '/'; do
        run_with_lib "SLURM_TMPDIR=\"\${T}/tmp/node\"; lab_rm_tmp '${rel}'"
        assert_status 2 "'${rel}'"
        assert_exists "${T}/tmp/node/keep" "'${rel}'"
        assert_exists "${T}/tmp/sentinel" "'${rel}'"
    done
}

# --- Real exit codes ----------------------------------------------------

# lab_run returns its command's code and writes it in the step line.
test_run_returns_the_real_code() {
    run_with_lib 'rc=0; lab_run step sh -c "exit 3" || rc=$?; echo "rc=${rc}"'
    assert_status 0
    assert_match "${T}/out" '^Step step finished with exit code 3 at: [0-9T:Z-]+$'
    assert_match "${T}/out" '^rc=3$'
}

# lab_run writes its step line before set -e ends the script.
test_run_writes_its_line_under_errexit() {
    run_with_lib <<'EOF'
set -euo pipefail
rc=0
lab_run step sh -c "exit 3" || rc=$?
echo "next ${rc}"
lab_run last false
echo not-reached
EOF
    assert_status 1
    assert_match "${T}/out" '^next 3$'
    assert_match "${T}/out" '^Step last finished with exit code 1 at: '
    assert_no_match "${T}/out" 'not-reached'
}

# A job script that fails ends with its real code in the job line.
test_job_line_has_the_real_code() {
    run_with_lib 'set -euo pipefail; lab_job_begin job; false; echo no'
    assert_status 1
    assert_match "${T}/out" '^Program finished with exit code 1 at: '
    assert_no_match "${T}/out" '^no$'
    run_with_lib 'set -euo pipefail; lab_job_begin job; exit 4'
    assert_status 4
    assert_match "${T}/out" '^Program finished with exit code 4 at: '
}

# A job script ended by TERM exits 143 and says so in its job line and
# its failure summary (bash runs the trap once sleep returns).
# shellcheck disable=SC2034  # STATUS is read by assert_status, in lib/helpers.sh
test_job_term_is_recorded() {
    cat >"${T}/case.sh" <<'EOF'
source "${LAB_LIB}"
set -euo pipefail
lab_job_begin job
: >"${T}/ready"
sleep 2
echo after
EOF
    "${BASH}" "${T}/case.sh" >"${T}/out" 2>"${T}/err" &
    local pid=$! i
    for ((i = 0; i < 100; i++)); do
        [[ -e "${T}/ready" ]] && break
        sleep 0.05
    done
    [[ -e "${T}/ready" ]] || fail "the job script never started"
    kill -TERM "${pid}"
    STATUS=0
    wait "${pid}" || STATUS=$?
    assert_status 143
    assert_match "${T}/err" 'received SIGTERM'
    assert_match "${T}/out" '^Program finished with exit code 143 at: '
    assert_match "${T}/out" '^  signal: TERM$'
    assert_no_match "${T}/out" '^after$'
}

# A job script that succeeds records 0 and writes no failure summary.
test_job_success_records_zero() {
    run_with_lib 'set -euo pipefail; lab_job_begin job; echo work'
    assert_status 0
    assert_match "${T}/out" '^Program finished with exit code 0 at: '
    assert_no_match "${T}/out" 'Failure summary'
}

# lab_last_status reads the last job line, says none without one, and
# legacy for a job line without the begin block.
test_last_status_reads_none_and_legacy() {
    printf 'Lab job begin at: t\nProgram finished with exit code 0 at: a\nProgram finished with exit code 5 at: b\n' >new.out
    printf 'Starting run at: t\n' >none.out
    printf 'Program finished with exit code 0 at: Tue Jan  2 00:00:00 2024\n' >old.out
    run_with_lib 'for f in new.out none.out absent.out old.out; do lab_last_status "$f"; done'
    assert_status 0
    assert_content "${T}/out" $'5\nnone\nnone\nlegacy'
}

# --- In-place edits -----------------------------------------------------

# lab_backup keeps the first original, with its mode.
test_backup_keeps_the_first_original() {
    printf 'one\n' >f
    chmod 640 f
    run_with_lib <<'EOF'
lab_backup f; echo "first=$?"
printf 'two\n' >f
rc=0; lab_backup f || rc=$?; echo "second=${rc}"
EOF
    assert_content "${T}/out" $'first=0\nsecond=1'
    assert_content f.orig one
    [[ -n "$(find f.orig -perm 640)" ]] || fail "f.orig lost its mode"
}

# lab_rewrite replaces the file only when its command succeeds.
test_rewrite_replaces_only_on_success() {
    printf 'a\n' >f
    chmod 640 f
    run_with_lib 'lab_rewrite f sed s/a/b/'
    assert_status 0
    assert_content f b
    assert_content f.orig a
    [[ -n "$(find f -perm 640)" ]] || fail "f lost its mode"
    printf 'a\n' >g
    run_with_lib 'rc=0; lab_rewrite g sh -c "cat >/dev/null; echo partial; exit 3" || rc=$?; echo "rc=${rc}"'
    assert_content "${T}/out" rc=3
    assert_content g a
    local left
    left="$(find . -name '.lab-rewrite.*')"
    [[ -z "${left}" ]] || fail "temporary file left: ${left}"
}

# --- Submitting ---------------------------------------------------------

# lab_sbatch under LAB_DRY_RUN=1 prints the command and calls nothing.
test_sbatch_dry_run_calls_nothing() {
    run_with_lib 'LAB_DRY_RUN=1 lab_sbatch --time=1:00 job.sh a'
    assert_status 0
    assert_content "${T}/out" 'dry run: sbatch --time=1:00 job.sh a'
    assert_not_called sbatch
}

# lab_sbatch passes its arguments unchanged and returns sbatch's code.
test_sbatch_passes_arguments_and_code() {
    run_with_lib 'lab_sbatch --time=1:00 "job one.sh" x; echo "rc=$?"'
    assert_content "${T}/out" rc=0
    [[ "$(stub_calls sbatch | cut -f2)" == 'sbatch --time=1:00 job\ one.sh x' ]] ||
        fail "sbatch got: $(stub_calls sbatch)"
    stub sbatch 'exit 1'
    run_with_lib 'rc=0; lab_sbatch job.sh || rc=$?; echo "rc=${rc}"'
    assert_content "${T}/out" rc=1
}

# lab_sbatch refuses an account or a mail address, even in a dry run.
test_sbatch_refuses_account_and_mail() {
    local args
    for args in '--account=x' '-A x' '-Ax' '--account x' '--mail-user=x' '--mail-user x'; do
        run_with_lib "rc=0; LAB_DRY_RUN=1 lab_sbatch ${args} job.sh || rc=\$?; rc2=0; lab_sbatch ${args} job.sh || rc2=\$?; echo \"rc=\${rc} \${rc2}\""
        assert_content "${T}/out" 'rc=2 2' "${args}"
    done
    assert_not_called sbatch
}

# --- What happened, when a job fails ------------------------------------

# The begin block lists the job's context, and unset for what is missing.
test_job_begin_block_lists_the_context() {
    run_with_lib <<'EOF'
SLURM_JOB_ID=123
SLURM_JOB_NODELIST="n[1-2]"
set -euo pipefail
lab_job_begin job
EOF
    assert_status 0
    assert_match "${T}/out" '^Lab job begin at: '
    assert_match "${T}/out" '^  job id: 123$'
    assert_match "${T}/out" '^  node list: n\[1-2\]$'
    assert_match "${T}/out" '^  array task id: unset$'
    assert_match "${T}/out" '^  lab commit: ([0-9a-f]+|unknown)$'
    assert_match "${T}/out" '^  working folder: '
    [[ "$(stub_calls module | cut -f2)" == "module list" ]] || fail "module list was not called"
}

# lab_run keeps a step's stderr in its file and on stderr, not on stdout.
test_run_keeps_stderr_in_a_file() {
    run_with_lib 'lab_run step sh -c "echo out; echo err >&2"'
    assert_status 0
    assert_match "${T}/out" '^out$'
    assert_no_match "${T}/out" '^err$'
    assert_match "${T}/err" '^err$'
    assert_content step.stderr err
}

# A Python traceback in a step's stderr is in the failure summary
# (Python's own output for an uncaught exception).
test_failure_summary_finds_a_traceback() {
    command -v python3 >/dev/null || skip "python3 not available"
    run_with_lib 'rc=0; lab_run py python3 -c "raise ValueError(\"x\")" || rc=$?; echo "rc=${rc}"'
    assert_match "${T}/out" '^rc=1$'
    assert_match "${T}/out" '^Failure summary for py:$'
    assert_match "${T}/out" '^  py\.stderr:1:Traceback \(most recent call last\):$'
    assert_match "${T}/out" '^  py\.stderr:[0-9]+:ValueError: x$'
}

# A LAMMPS error line, with or without srun's task label, is in the
# summary with its file and line number, and a thermo line is not.
test_failure_summary_finds_a_lammps_error() {
    cat >log.lammps <<'EOF'
Step Temp E_pair
       0    1.0   -6.7
     100    1.1   -6.6
ERROR on proc 3: Lost atoms: original 400 current 399 (src/thermo.cpp:488)
2: ERROR: Out of range atoms - cannot compute PPPM (src/KSPACE/pppm.cpp:1925)
EOF
    run_with_lib 'rc=0; lab_run -f log.lammps lmp sh -c "exit 1" || rc=$?'
    assert_match "${T}/out" '^  log\.lammps:4:ERROR on proc 3: Lost atoms'
    assert_match "${T}/out" '^  log\.lammps:5:2: ERROR: Out of range atoms'
    assert_no_match "${T}/out" 'log\.lammps:[23]:'
}

# Each srun and slurmstepd pattern finds its own line, and an ordinary
# line is found by none. The lines are made up, one pattern each.
test_failure_summary_finds_slurm_lines() {
    cat >slurm-1.out <<'EOF'
Lab job begin at: 2026-01-01T00:00:00Z
an ordinary line
srun: error: nodeX: task 5: Killed
slurmstepd: error: step 1.0 failed
Detected 1 oom_kill event in step 1.0
*** JOB 1 ON nodeX DUE TO TIME LIMIT ***
*** JOB 1 CANCELLED AT 2026-01-01T01:00:00 ***
JOB 1 ended with state NODE_FAIL
another ordinary line
EOF
    : >empty.stderr
    run_with_lib 'lab_failure_summary job 1 empty.stderr slurm-1.out'
    assert_status 0
    local line
    for line in 3 4 5 6 7 8; do
        assert_match "${T}/out" "^  slurm-1\\.out:${line}:"
    done
    assert_no_match "${T}/out" 'ordinary'
}

# With no pattern the summary shows the stderr's last lines, and with no
# stderr either it says that no reason was found.
test_failure_summary_without_a_pattern() {
    run_with_lib 'rc=0; lab_run tail sh -c "for i in \$(seq 1 30); do echo line\$i >&2; done; exit 1" || rc=$?'
    assert_match "${T}/out" '^  no known pattern; the last lines of tail\.stderr:$'
    assert_match "${T}/out" '^  \| line11$'
    assert_match "${T}/out" '^  \| line30$'
    assert_no_match "${T}/out" '^  \| line10$'
    run_with_lib 'rc=0; lab_run quiet sh -c "exit 1" || rc=$?'
    assert_match "${T}/out" '^  no reason found in: quiet\.stderr$'
}

# lab_job_state prints each step's line from accounting, in order.
test_job_state_prints_each_step() {
    stub sacct "printf '%s\n' '123|COMPLETED|0:0|n1|00:01:00|10K|3G' '123.batch|TIMEOUT|0:15|n1|1-00:00:00|2G|3G' '123.0|OUT_OF_MEMORY|0:125|n1|00:10:00|3G|3G' '123.1|NODE_FAIL|1:0|n2|00:20:00||3G'"
    run_with_lib 'lab_job_state 123'
    assert_status 0
    assert_content "${T}/out" $'123|COMPLETED|0:0|n1|00:01:00|10K|3G\n123.batch|TIMEOUT|0:15|n1|1-00:00:00|2G|3G\n123.0|OUT_OF_MEMORY|0:125|n1|00:10:00|3G|3G\n123.1|NODE_FAIL|1:0|n2|00:20:00||3G'
    local expected
    expected="sacct$(printf ' %q' -n -P -j 123 --format=JobID,State,ExitCode,NodeList,Elapsed,MaxRSS,ReqMem)"
    [[ "$(stub_calls sacct | cut -f2)" == "${expected}" ]] ||
        fail "sacct got: $(stub_calls sacct)"
}

# lab_job_state refuses with code 2 without sacct, or for a bad job id.
test_job_state_refuses_without_sacct() {
    mkdir -p "${T}/only"
    ln -s "$(command -v date)" "${T}/only/date"
    run_with_lib 'PATH="${T}/only"; rc=0; lab_job_state 123 || rc=$?; echo "rc=${rc}"'
    assert_content "${T}/out" rc=2
    assert_match "${T}/err" 'sacct'
    run_with_lib 'rc=0; lab_job_state "1;2" || rc=$?; echo "rc=${rc}"'
    assert_content "${T}/out" rc=2
    assert_not_called sacct
}
