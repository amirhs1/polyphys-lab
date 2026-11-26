# shellcheck shell=bash
# The shell functions that every pipeline stage and every study's slurm/
# wrapper shares. Sourced, never run:
#
#     # shellcheck source=../lib/common.sh
#     source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
#
# pipeline/lib/README.md documents each function. Sourcing this file sets no
# shell option and installs no trap; the caller sets `set -euo pipefail`.
# Exit codes: 0 success, 1 a step failed, 2 refused (a usage error, a
# missing or invalid setting, or a guard), 128 + N ended by signal N.

# The checks before the first function use only syntax that bash 3.2
# parses, so an old bash reaches them and says why it stops.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "${0##*/}: a library to source, not a command to run" >&2
    exit 2
fi
if [ -z "${BASH_VERSINFO[0]:-}" ] || [ "${BASH_VERSINFO[0]}" -lt 4 ] ||
    { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -lt 4 ]; }; then
    echo "common.sh: bash ${BASH_VERSION:-unknown} found; 4.4 or later is needed" >&2
    return 2
fi
if [ -n "${LAB_COMMON_LOADED:-}" ]; then
    return 0
fi
LAB_COMMON_LOADED=1

# The lab's root, from this file's own path.
LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)" || {
    echo "common.sh: cannot find the lab's root" >&2
    return 2
}

# The lines that say why a step failed, as extended regular expressions,
# each with its source. A pattern is added only with its source. An
# optional "N: " prefix allows for `srun --label`.
#   LAMMPS: its error messages, "ERROR:" and "ERROR on proc N:".
#   Python: a traceback's first line and the exception line that ends it.
#   SLURM: srun and slurmstepd messages and job states; not yet checked
#   against real output.
LAB_FAILURE_PATTERNS=(
    '^([0-9]+: )?ERROR( on proc [0-9]+)?:'
    '^([0-9]+: )?Traceback \(most recent call last\):'
    '^([0-9]+: )?[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Interrupt)(:|$)'
    'srun: error:'
    'slurmstepd: error:'
    'oom[-_]kill'
    'DUE TO TIME LIMIT'
    'CANCELLED'
    'NODE_FAIL'
)
LAB_FAILURE_MAX_LINES=40
LAB_FAILURE_TAIL_LINES=20

# --- Logging ------------------------------------------------------------

# lab__now: the UTC time, as in every log and status line.
lab__now() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

lab__line() { # lab__line LEVEL MESSAGE...
    local level=$1
    shift
    printf '%s %s %s: %s\n' "$(lab__now)" "${0##*/}" "${level}" "$*" >&2
}

# lab_log MESSAGE...: one line on stderr.
lab_log() {
    lab__line info "$@"
}

# lab_warn MESSAGE...: one warning line on stderr.
lab_warn() {
    lab__line warn "$@"
}

# lab__error MESSAGE...: one error line on stderr, without exiting.
lab__error() {
    lab__line error "$@"
}

# lab_die [-c CODE] MESSAGE...: an error line on stderr, then exit CODE
# (default 1).
lab_die() {
    local code=1
    if [[ "${1-}" == -c ]]; then
        code="${2-1}"
        shift 2 || shift $#
    fi
    [[ "${code}" =~ ^[0-9]+$ ]] || code=1
    lab__error "$@"
    exit "${code}"
}

# --- Names and variables ------------------------------------------------

# lab__check_var_name NAME: refuse a name that cannot be a variable, or
# that would shadow one of this library's own locals.
lab__check_var_name() {
    [[ "${1-}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && "${1-}" != __lab_* ]] ||
        lab_die -c 2 "not a usable variable name: '${1-}'"
}

# lab_check_name KIND VALUE: a study or variant name is lowercase letters,
# digits, and underscores, starting with a letter or a digit.
lab_check_name() {
    local pattern='^[a-z0-9][a-z0-9_]*$'
    [[ "${2-}" =~ ${pattern} ]] ||
        lab_die -c 2 "not a valid ${1-name} name: '${2-}'"
}

# lab_require VAR...: every VAR is set, not empty, and not a CHANGE_ME
# placeholder; otherwise die with code 2, naming every one at fault.
lab_require() {
    local var faults=()
    for var in "$@"; do
        lab__check_var_name "${var}"
        if [[ ! -v "${var}" ]]; then
            faults+=("${var} (unset)")
        elif [[ -z "${!var}" ]]; then
            faults+=("${var} (empty)")
        elif [[ "${!var}" == *CHANGE_ME* ]]; then
            faults+=("${var} (still CHANGE_ME)")
        fi
    done
    if ((${#faults[@]})); then
        lab_die -c 2 "settings missing: $(printf '%s; ' "${faults[@]}")"
    fi
}

# --- Site settings: cluster.conf ----------------------------------------

# lab_load_cluster_conf: source LAB_CLUSTER_CONF, else the lab's
# config/cluster.conf; die with code 2 if it is missing or does not parse.
lab_load_cluster_conf() {
    local conf="${LAB_CLUSTER_CONF:-${LAB_ROOT}/config/cluster.conf}"
    if [[ ! -f "${conf}" ]]; then
        lab_die -c 2 "no site settings at ${conf}; copy" \
            "${LAB_ROOT}/config/cluster.conf.example to" \
            "${LAB_ROOT}/config/cluster.conf and fill it in"
    fi
    "${BASH}" -n "${conf}" || lab_die -c 2 "syntax error in ${conf}"
    # shellcheck source=/dev/null
    source "${conf}" || lab_die -c 2 "could not read ${conf}"
    lab_log "read site settings from ${conf}"
}

# --- Finding a study: study.conf ----------------------------------------

lab__list() { # lab__list GLOB_PREFIX GLOB_SUFFIX: the names that match
    local path names=()
    for path in "$1"*"$2"; do
        [[ -e "${path}" ]] || continue
        path="${path%"$2"}"
        names+=("${path##*/}")
    done
    if ((${#names[@]})); then
        printf '%s' "${names[0]}"
        ((${#names[@]} == 1)) || printf ', %s' "${names[@]:1}"
    else
        printf 'none'
    fi
}

# lab_study_conf VAR STUDY VARIANT: set VAR to the variant's study.conf
# under LAB_PROJECTS_DIR (default: the lab's projects/), or die with code 2
# and list what exists.
lab_study_conf() {
    lab__check_var_name "${1-}"
    lab__study_conf "$@"
}

# lab__study_conf: lab_study_conf without the check of VAR, for this
# library's own callers.
lab__study_conf() {
    lab_check_name study "${2-}"
    lab_check_name variant "${3-}"
    local __lab_sc_root="${LAB_PROJECTS_DIR:-${LAB_ROOT}/projects}"
    [[ -d "${__lab_sc_root}" ]] ||
        lab_die -c 2 "no projects folder at ${__lab_sc_root}"
    if [[ ! -d "${__lab_sc_root}/$2" ]]; then
        lab_die -c 2 "no study '$2' in ${__lab_sc_root}; studies:" \
            "$(lab__list "${__lab_sc_root}/" /)"
    fi
    local __lab_sc_conf="${__lab_sc_root}/$2/lammps/$3/study.conf"
    if [[ ! -f "${__lab_sc_conf}" ]]; then
        lab_die -c 2 "no variant '$3' of study '$2'; variants:" \
            "$(lab__list "${__lab_sc_root}/$2/lammps/" /study.conf)"
    fi
    printf -v "$1" '%s' "${__lab_sc_conf}"
}

# lab_load_study STUDY VARIANT: source the variant's study.conf and check
# that it names itself; die with code 2 otherwise.
lab_load_study() {
    local __lab_ls_conf
    lab__study_conf __lab_ls_conf "${1-}" "${2-}"
    "${BASH}" -n "${__lab_ls_conf}" ||
        lab_die -c 2 "syntax error in ${__lab_ls_conf}"
    unset STUDY VARIANT
    # shellcheck source=/dev/null
    source "${__lab_ls_conf}" || lab_die -c 2 "could not read ${__lab_ls_conf}"
    if [[ "${STUDY-}" != "$1" || "${VARIANT-}" != "$2" ]]; then
        lab_die -c 2 "${__lab_ls_conf} names STUDY='${STUDY-}'" \
            "VARIANT='${VARIANT-}', not '$1' and '$2'"
    fi
    lab_log "read ${__lab_ls_conf}"
}

# --- The node-local folder: SLURM_TMPDIR --------------------------------

# lab__tmpdir_check VAR: set VAR to the resolved SLURM_TMPDIR, or log why
# not and return 2.
lab__tmpdir_check() {
    if [[ ! -v SLURM_TMPDIR ]]; then
        lab__error "SLURM_TMPDIR is not set: this step runs only inside a job"
        return 2
    fi
    if [[ -z "${SLURM_TMPDIR}" ]]; then
        lab__error "SLURM_TMPDIR is empty"
        return 2
    fi
    if [[ ! -d "${SLURM_TMPDIR}" ]]; then
        lab__error "SLURM_TMPDIR is not a folder: ${SLURM_TMPDIR}"
        return 2
    fi
    local __lab_tc_dir
    __lab_tc_dir="$(cd -- "${SLURM_TMPDIR}" && pwd -P)" || return 2
    if [[ "${__lab_tc_dir}" =~ ^/+$ ]]; then
        lab__error "SLURM_TMPDIR is the root folder"
        return 2
    fi
    if [[ ! -w "${__lab_tc_dir}" ]]; then
        lab__error "SLURM_TMPDIR is not writable: ${__lab_tc_dir}"
        return 2
    fi
    printf -v "$1" '%s' "${__lab_tc_dir}"
}

# lab__tmp_rel_check RELATIVE: a path inside the tmpdir: not empty, not
# absolute, and with no "." or ".." component; otherwise log and return 2.
lab__tmp_rel_check() {
    local rel="${1-}"
    if [[ -z "${rel}" || "${rel}" == /* || "/${rel}/" == */../* ||
        "/${rel}/" == */./* ]]; then
        lab__error "not a path inside SLURM_TMPDIR: '${rel}'"
        return 2
    fi
}

# lab_tmpdir VAR: set VAR to SLURM_TMPDIR after checking it; die with
# code 2 when it is unset, empty, /, not a folder, or not writable.
lab_tmpdir() {
    lab__check_var_name "${1-}"
    lab__tmpdir_check "$1" || lab_die -c 2 "refusing to use SLURM_TMPDIR"
}

# lab_tmp_path VAR RELATIVE: set VAR to SLURM_TMPDIR/RELATIVE, or die
# with code 2.
lab_tmp_path() {
    lab__check_var_name "${1-}"
    local __lab_tp_dir
    lab__tmpdir_check __lab_tp_dir || lab_die -c 2 "refusing to use SLURM_TMPDIR"
    lab__tmp_rel_check "${2-}" || lab_die -c 2 "refusing the path '${2-}'"
    printf -v "$1" '%s/%s' "${__lab_tp_dir}" "$2"
}

# lab_rm_tmp RELATIVE: remove SLURM_TMPDIR/RELATIVE, never the tmpdir
# itself; return 2 when a check fails, else rm's code.
lab_rm_tmp() {
    local __lab_rm_dir
    lab__tmpdir_check __lab_rm_dir || return 2
    lab__tmp_rel_check "${1-}" || return 2
    rm -rf -- "${__lab_rm_dir:?}/${1:?}"
}

# --- In-place edits -----------------------------------------------------

# lab_backup FILE: copy FILE to FILE.orig, keeping its mode and time;
# return 1 and touch nothing when FILE.orig exists, 2 when FILE does not.
lab_backup() {
    local file="${1-}"
    if [[ ! -f "${file}" ]]; then
        lab__error "no file to back up: '${file}'"
        return 2
    fi
    if [[ -e "${file}.orig" || -L "${file}.orig" ]]; then
        lab__error "${file}.orig exists; the first original is kept"
        return 1
    fi
    cp -p -- "${file}" "${file}.orig"
}

# lab_rewrite FILE COMMAND [ARGS...]: back FILE up, run COMMAND with
# FILE.orig on stdin, and replace FILE with its output only if it exits 0.
# Returns COMMAND's code; on failure FILE is unchanged.
lab_rewrite() {
    local file="${1-}"
    shift || true
    if (($# == 0)); then
        lab__error "lab_rewrite needs a file and a command"
        return 2
    fi
    lab_backup "${file}" || return
    local tmp rc=0
    tmp="$(mktemp "$(dirname -- "${file}")/.lab-rewrite.XXXXXX")" || return 1
    cp -p -- "${file}.orig" "${tmp}" || {
        rm -f -- "${tmp}"
        return 1
    }
    "$@" <"${file}.orig" >"${tmp}" || rc=$?
    if ((rc == 0)); then
        mv -f -- "${tmp}" "${file}" || {
            rc=$?
            rm -f -- "${tmp}"
        }
    else
        rm -f -- "${tmp}"
        lab__error "rewrite of ${file} failed with code ${rc}; the file is unchanged"
    fi
    return "${rc}"
}

# --- Real exit codes and what happened ----------------------------------

lab__check_label() {
    [[ "${1-}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
        lab_die -c 2 "not a usable label: '${1-}'"
}

# lab_failure_summary LABEL CODE [FILE...]: after a failure, print what
# the files say about it: the signal, the lines that match
# LAB_FAILURE_PATTERNS, or else the last lines of the first file.
lab_failure_summary() {
    local label="${1-}" code="${2-}"
    shift 2 || shift $#
    printf 'Failure summary for %s:\n' "${label}"
    if [[ "${code}" =~ ^[0-9]+$ ]] && ((code > 128 && code < 160)); then
        printf '  signal: %s\n' "$(kill -l "$((code - 128))" 2>/dev/null || echo "$((code - 128))")"
    fi
    local args=() pattern file
    for pattern in "${LAB_FAILURE_PATTERNS[@]}"; do
        args+=(-e "${pattern}")
    done
    local found=0 read_files=() line
    for file in "$@"; do
        [[ -f "${file}" ]] || continue
        read_files+=("${file}")
        while IFS= read -r line; do
            ((found < LAB_FAILURE_MAX_LINES)) || break
            printf '  %s:%s\n' "${file}" "${line}"
            found=$((found + 1))
        done < <(grep -nE "${args[@]}" -- "${file}" || true)
    done
    if ((found == 0)) && [[ -s "${1-}" ]]; then
        printf '  no known pattern; the last lines of %s:\n' "$1"
        tail -n "${LAB_FAILURE_TAIL_LINES}" -- "$1" | sed 's/^/  | /'
    elif ((found == 0)); then
        if ((${#read_files[@]})); then
            printf '  no reason found in: %s\n' "${read_files[*]}"
        else
            printf '  no reason found in: no file to read\n'
        fi
    fi
}

# lab_run [-o FILE] [-f FILE]... LABEL COMMAND [ARGS...]: run COMMAND,
# keep its stderr in LABEL.stderr and copy it to stderr, write the step
# line with its real code, and, on failure, a summary that also reads each
# -f FILE (such as log.lammps). With -o, COMMAND's stdout goes to FILE.
# Returns COMMAND's code.
lab_run() {
    local out="" files=()
    while (($#)); do
        case "$1" in
            -o)
                out="${2:?lab_run -o needs a file}"
                shift 2
                ;;
            -f)
                files+=("${2:?lab_run -f needs a file}")
                shift 2
                ;;
            *) break ;;
        esac
    done
    local label="${1-}"
    lab__check_label "${label}"
    shift
    (($#)) || lab_die -c 2 "lab_run ${label}: no command"
    local err="${label}.stderr" rc=0
    LAB__STEP_ERR="${PWD}/${err}"
    if [[ -n "${out}" ]]; then
        "$@" >"${out}" 2>"${err}" || rc=$?
    else
        "$@" 2>"${err}" || rc=$?
    fi
    cat -- "${err}" >&2 || true
    printf 'Step %s finished with exit code %s at: %s\n' "${label}" "${rc}" "$(lab__now)"
    if ((rc != 0)); then
        lab_failure_summary "${label}" "${rc}" "${err}" "${files[@]}"
    fi
    LAB__STEP_ERR=""
    return "${rc}"
}

# lab_last_status FILE: print the code of FILE's last job line, "none"
# when there is none, or "legacy" when FILE has a job line but no begin
# block, so an old script's line is never read as a real code.
lab_last_status() {
    local file="${1-}" line
    if [[ ! -f "${file}" ]]; then
        printf 'none\n'
        return 0
    fi
    line="$(grep -E '^Program finished with exit code [0-9]+ at: ' -- "${file}" |
        tail -n 1)" || true
    if [[ -z "${line}" ]]; then
        printf 'none\n'
    elif ! grep -q '^Lab job begin at: ' -- "${file}"; then
        printf 'legacy\n'
    else
        line="${line#Program finished with exit code }"
        printf '%s\n' "${line%% *}"
    fi
}

lab__begin_block() {
    local commit modules
    commit="$(git -C "${LAB_ROOT}" rev-parse --short HEAD 2>/dev/null)" ||
        commit=unknown
    if declare -F module >/dev/null || command -v module >/dev/null; then
        modules="$(module list 2>&1 | sed 's/^/    /')" || true
    else
        modules="    (no module command)"
    fi
    printf 'Lab job begin at: %s\n' "$(lab__now)"
    printf '  label: %s\n' "${LAB__JOB_LABEL}"
    printf '  job id: %s\n' "${SLURM_JOB_ID:-unset}"
    printf '  array task id: %s\n' "${SLURM_ARRAY_TASK_ID:-unset}"
    printf '  job name: %s\n' "${SLURM_JOB_NAME:-unset}"
    printf '  node list: %s\n' "${SLURM_JOB_NODELIST:-unset}"
    printf '  nodes: %s\n' "${SLURM_JOB_NUM_NODES:-unset}"
    printf '  tasks: %s\n' "${SLURM_NTASKS:-unset}"
    printf '  CPUs per task: %s\n' "${SLURM_CPUS_PER_TASK:-unset}"
    printf '  memory per CPU: %s\n' "${SLURM_MEM_PER_CPU:-unset}"
    printf '  host: %s\n' "${HOSTNAME:-unknown}"
    printf '  working folder: %s\n' "${PWD}"
    printf '  bash: %s\n' "${BASH_VERSION}"
    printf '  lab commit: %s\n' "${commit}"
    printf '  modules:\n%s\n' "${modules}"
}

lab__on_exit() {
    local rc=$?
    printf 'Program finished with exit code %s at: %s\n' "${rc}" "$(lab__now)"
    if ((rc != 0)); then
        local files=()
        [[ -z "${LAB__STEP_ERR:-}" ]] || files+=("${LAB__STEP_ERR}")
        lab_failure_summary "${LAB__JOB_LABEL}" "${rc}" "${files[@]}"
    fi
}

lab__on_signal() { # lab__on_signal NAME NUMBER
    lab__error "received SIG$1"
    exit "$((128 + $2))"
}

# lab_job_begin LABEL: at the top of a job script, after its own
# `set -euo pipefail`: write the begin block, and install the traps that
# write the job line with the script's real exit code and end it with
# 128 + N on TERM or INT.
lab_job_begin() {
    lab__check_label "${1-}"
    LAB__JOB_LABEL="$1"
    LAB__STEP_ERR=""
    lab__begin_block
    trap lab__on_exit EXIT
    trap 'lab__on_signal TERM 15' TERM
    trap 'lab__on_signal INT 2' INT
}

# lab_job_state JOBID: one line per step of the job from SLURM's
# accounting: step, state, exit code, node list, elapsed time, maximum
# resident memory, requested memory. Returns 2 without sacct.
lab_job_state() {
    if [[ ! "${1-}" =~ ^[0-9]+(_[0-9]+)?$ ]]; then
        lab__error "not a job id: '${1-}'"
        return 2
    fi
    if ! command -v sacct >/dev/null; then
        lab__error "sacct is not available here; run this where SLURM is"
        return 2
    fi
    sacct -n -P -j "$1" \
        --format=JobID,State,ExitCode,NodeList,Elapsed,MaxRSS,ReqMem
}

# --- Submitting ---------------------------------------------------------

# lab_sbatch [SBATCH ARGS...] SCRIPT [ARGS...]: call sbatch with these
# arguments unchanged, or only print the command when LAB_DRY_RUN=1.
# Refuses (code 2) any argument that sets the account or a mail address.
lab_sbatch() {
    local arg
    for arg in "$@"; do
        case "${arg}" in
            -A | -A?* | --account | --account=* | --mail-user | --mail-user=*)
                lab__error "refusing '${arg}': the account comes from" \
                    "SBATCH_ACCOUNT, and no address is passed"
                return 2
                ;;
        esac
    done
    if [[ "${LAB_DRY_RUN:-}" == 1 ]]; then
        printf 'dry run: sbatch'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi
    if ! command -v sbatch >/dev/null; then
        lab__error "sbatch is not available here"
        return 2
    fi
    sbatch "$@"
}
