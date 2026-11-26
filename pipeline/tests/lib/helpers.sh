# shellcheck shell=bash
# Helpers of the shell test harness, sourced by lib/run_one.sh before each
# test. Every test runs in its own bash process and sandbox, so nothing
# here cleans up after another test.
#
# After _setup a test can rely on:
#   T              the sandbox root, a fresh mktemp folder
#   W              the working folder, $T/a/b/c/work: nested, so a script
#                  that climbs with `cd ..` stays inside the sandbox
#   STUB_LOG       one line per stub call: "<folder><TAB><name> <args...>"
#   STATUS         the exit code of the last run_script or run_with_lib
#   LAB_TEST_ROOT  the lab under test (exported by run_tests.sh)
#   LAB_LIB        $LAB_TEST_ROOT/pipeline/lib/common.sh

# The cluster commands that are stubs in every test.
STUBBED_COMMANDS=(sbatch srun scancel squeue sacct rsync module parallel)

# --- Sandbox ------------------------------------------------------------

_setup() {
    T="$(mktemp -d "${TMPDIR:-/tmp}/lab-test.XXXXXX")"
    T="$(cd "${T}" && pwd -P)"
    trap _teardown EXIT
    W="${T}/a/b/c/work"
    mkdir -p "${W}" "${T}/home" "${T}/bin"
    export T W

    # Nothing under test may reach the real home folder, the real cluster
    # commands, or settings inherited from the caller's shell.
    export HOME="${T}/home"
    export PATH="${T}/bin:${PATH}"
    export STUB_LOG="${T}/stub.log"
    : >"${STUB_LOG}"
    unset LAB_CLUSTER_CONF LAB_PROJECTS_DIR LAB_DRY_RUN LAB_COMMON_LOADED
    local var
    for var in "${!SLURM_@}"; do
        unset "${var}"
    done
    unset -f module ml 2>/dev/null || true
    LAB_LIB="${LAB_TEST_ROOT}/pipeline/lib/common.sh"
    export LAB_LIB

    local name
    for name in "${STUBBED_COMMANDS[@]}"; do
        stub "${name}"
    done

    cd "${W}" || exit 1
}

_teardown() {
    cd / || return 0
    [[ -n "${T:-}" && -d "${T}" && "${T}" == */lab-test.* ]] || return 0
    chmod -R u+rwx "${T}" 2>/dev/null || true
    rm -rf -- "${T:?}"
}

# --- Outcomes -----------------------------------------------------------

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

# Exit code 77 is the automake convention for a skipped test.
skip() {
    printf 'SKIP: %s\n' "$*" >&2
    exit 77
}

# --- Running code under test --------------------------------------------

_show_run() {
    if [[ -n "${LAB_TEST_VERBOSE:-}" ]]; then
        printf -- '--- %s (exit %s)\n' "$1" "${STATUS}" >&2
        sed 's/^/  out| /' "${T}/out" >&2
        sed 's/^/  err| /' "${T}/err" >&2
    fi
}

# run_script [--stdin TEXT] SCRIPT [ARGS...]
#   Runs SCRIPT (a path) with the harness's bash. stdin is /dev/null
#   unless --stdin is given. stdout and stderr go to $T/out and $T/err,
#   the exit code to STATUS.
run_script() {
    local input="" has_input=0
    if [[ "${1:-}" == --stdin ]]; then
        input="$2"
        has_input=1
        shift 2
    fi
    local script="$1"
    shift
    [[ -f "${script}" ]] || fail "script under test not found: ${script}"
    STATUS=0
    if ((has_input)); then
        printf '%s\n' "${input}" |
            "${BASH}" "${script}" "$@" >"${T}/out" 2>"${T}/err" || STATUS=$?
    else
        "${BASH}" "${script}" "$@" </dev/null >"${T}/out" 2>"${T}/err" || STATUS=$?
    fi
    _show_run "${script##*/}"
}

# run_with_lib [CODE]
#   Writes $T/case.sh: a script that sources the library under test and
#   then runs CODE, or stdin when CODE is not given, and runs it with
#   run_script in the working folder. CODE sets its own shell options; it
#   sees T, W, and LAB_LIB in its environment.
run_with_lib() {
    local code
    if (($#)); then
        code="$1"
    else
        code="$(cat)"
    fi
    {
        printf 'source "%s"\n' "${LAB_LIB}"
        printf '%s\n' "${code}"
    } >"${T}/case.sh"
    run_script "${T}/case.sh"
}

# write_case CODE: writes CODE alone to $T/case.sh, for a test that
# sources the library itself.
write_case() {
    printf '%s\n' "$1" >"${T}/case.sh"
}

# --- Stubs --------------------------------------------------------------

# stub NAME [SHELL-CODE]
#   Puts an executable NAME first on PATH that logs its folder and
#   arguments to STUB_LOG, then runs SHELL-CODE, if any.
stub() {
    local name="$1" body="${2:-}"
    cat >"${T}/bin/${name}" <<STUB
#!/usr/bin/env bash
{ printf '%s\t%s' "\${PWD}" "${name}"; printf ' %q' "\$@"; printf '\n'; } >>"${STUB_LOG}"
${body}
STUB
    chmod +x "${T}/bin/${name}"
}

unstub() {
    rm -f -- "${T}/bin/$1"
}

# stub_calls NAME: the logged calls to NAME, one per line.
stub_calls() {
    awk -F'\t' -v n="$1" '{ split($2, a, " "); if (a[1] == n) print }' "${STUB_LOG}"
}

# --- Fixtures -----------------------------------------------------------

# snapshot DIR: an order-independent checksum of every file under DIR.
snapshot() {
    (cd "$1" && find . -type f -exec cksum {} + | sort)
}

# make_study ROOT STUDY VARIANT [STUDY_IN_FILE] [VARIANT_IN_FILE]
#   Builds ROOT/STUDY/lammps/VARIANT/study.conf, naming itself, or the
#   names given.
make_study() {
    local dir="$1/$2/lammps/$3"
    mkdir -p "${dir}"
    cat >"${dir}/study.conf" <<CONF
STUDY="${4:-$2}"
VARIANT="${5:-$3}"
SWEEP=(
    "1 2 3"
)
CONF
}

# --- Assertions ---------------------------------------------------------

assert_status() { # assert_status CODE [WHAT]
    [[ "${STATUS}" -eq "$1" ]] || fail "${2:-exit status}: expected $1, got ${STATUS}"
}

assert_exists() { # assert_exists PATH [MESSAGE]
    [[ -e "$1" ]] || fail "${2:-expected to exist}: $1"
}

assert_missing() { # assert_missing PATH [MESSAGE]
    [[ ! -e "$1" ]] || fail "${2:-expected to be absent}: $1"
}

assert_content() { # assert_content FILE EXPECTED [MESSAGE]
    [[ -f "$1" ]] || fail "${3:-missing file}: $1"
    local got
    got="$(cat -- "$1")"
    [[ "${got}" == "$2" ]] || fail "${3:-content of $1}: expected '$2', got '${got}'"
}

assert_match() { # assert_match FILE ERE [MESSAGE]
    grep -qE -- "$2" "$1" || fail "${3:-$1 should match} /$2/; it holds:"$'\n'"$(cat -- "$1")"
}

assert_no_match() { # assert_no_match FILE ERE [MESSAGE]
    ! grep -qE -- "$2" "$1" || fail "${3:-$1 should not match} /$2/: $(grep -E -- "$2" "$1" | head -n 3)"
}

assert_empty() { # assert_empty FILE [MESSAGE]
    [[ ! -s "$1" ]] || fail "${2:-$1 should be empty}: $(head -n 3 -- "$1")"
}

assert_not_called() { # assert_not_called NAME [MESSAGE]
    local calls
    calls="$(stub_calls "$1")"
    [[ -z "${calls}" ]] || fail "${2:-$1 should not have run}: ${calls}"
}
