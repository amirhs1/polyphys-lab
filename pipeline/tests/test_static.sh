# shellcheck shell=bash
# Static checks of the pipeline's files. Nothing is executed. Each check
# reads the lab under test: its pipeline/, its studies' slurm/ folders, and
# config/cluster.conf.example.

# Every *.sh file under pipeline/.
_pipeline_scripts() {
    find "${LAB_TEST_ROOT}/pipeline" -type f -name '*.sh' | sort
}

# The stage scripts and the studies' wrappers: the files that run jobs.
_job_scripts() {
    {
        find "${LAB_TEST_ROOT}/pipeline" -type f -name '*.sh' -path '*/pipeline/[1-6]-*'
        find "${LAB_TEST_ROOT}"/projects/*/slurm -type f -name '*.sh' 2>/dev/null || true
    } | sort
}

# Every file under pipeline/ and the studies' slurm/, and the example.
_all_files() {
    {
        find "${LAB_TEST_ROOT}/pipeline" -type f ! -name '.DS_Store'
        find "${LAB_TEST_ROOT}"/projects/*/slurm -type f 2>/dev/null || true
        printf '%s\n' "${LAB_TEST_ROOT}/config/cluster.conf.example"
    } | sort
}

# _hits ERE FILE...: the "file:line:text" of each non-comment line that
# matches.
_hits() {
    local pattern="$1"
    shift
    (($#)) || return 0
    grep -nHE -- "^[^#]*${pattern}" "$@" 2>/dev/null |
        sed "s|^${LAB_TEST_ROOT}/||" || true
}

# Every shell file under pipeline/ parses.
test_static_every_script_parses() {
    local f bad=()
    while IFS= read -r f; do
        "${BASH}" -n "${f}" 2>/dev/null || bad+=("${f#"${LAB_TEST_ROOT}"/}")
    done < <(_pipeline_scripts)
    ((${#bad[@]} == 0)) || fail "syntax errors in: ${bad[*]}"
}

# Only the library names SLURM_TMPDIR; every job script goes through it.
test_static_tmpdir_only_in_the_library() {
    local files=() hits
    mapfile -t files < <(_job_scripts)
    ((${#files[@]})) || return 0
    hits="$(grep -nH 'SLURM_TMPDIR' "${files[@]}" | sed "s|^${LAB_TEST_ROOT}/||" || true)"
    [[ -z "${hits}" ]] || fail "SLURM_TMPDIR outside the library:"$'\n'"${hits}"
}

# No job script or library line edits a file in place.
test_static_no_in_place_edit() {
    local files=() hits
    mapfile -t files < <(_job_scripts)
    files+=("${LAB_TEST_ROOT}/pipeline/lib/common.sh")
    hits="$(_hits '(^|[^[:alnum:]_])(sed|perl)[[:space:]]([^#]*[[:space:]])?(-[[:alpha:]]*i|--in-place)' "${files[@]}")"
    [[ -z "${hits}" ]] || fail "in-place edits:"$'\n'"${hits}"
}

# No #SBATCH account or mail line, e-mail address, or allocation code.
test_static_no_identity() {
    local files=() hits
    mapfile -t files < <(_all_files)
    hits="$(grep -nHE -e '^#SBATCH[[:space:]]+--(account|mail-user)' \
        -e '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
        -e '(^|[^[:alnum:]])(def|rrg)-[a-z]{3,}' "${files[@]}" 2>/dev/null |
        sed "s|^${LAB_TEST_ROOT}/||" || true)"
    [[ -z "${hits}" ]] || fail "identity in a tracked file:"$'\n'"${hits}"
}

# The pipeline is ShellCheck-clean as CI calls it, and the example is
# clean as bash.
test_static_shellcheck_clean() {
    command -v shellcheck >/dev/null || skip "shellcheck not installed"
    local files=() out
    mapfile -t files < <(_pipeline_scripts)
    out="$(cd "${LAB_TEST_ROOT}" && shellcheck "${files[@]}" 2>&1)" ||
        fail "ShellCheck findings:"$'\n'"${out}"
    out="$(cd "${LAB_TEST_ROOT}" && shellcheck -s bash config/cluster.conf.example 2>&1)" ||
        fail "ShellCheck findings in the example:"$'\n'"${out}"
}

# Every stage script starts with #!/bin/bash, sets the strict options,
# and sources the library.
test_static_stage_scripts_have_the_header() {
    local f bad=()
    # shellcheck disable=SC2016  # the literal line a stage holds
    local source_line='source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"'
    for f in "${LAB_TEST_ROOT}"/pipeline/[1-6]-*/*.sh; do
        [[ -f "${f}" ]] || continue
        [[ "$(head -n 1 "${f}")" == '#!/bin/bash' ]] || bad+=("${f##*/}: shebang")
        grep -qx 'set -euo pipefail' "${f}" || bad+=("${f##*/}: set -euo pipefail")
        grep -qxF "${source_line}" "${f}" || bad+=("${f##*/}: source line")
    done
    ((${#bad[@]} == 0)) || fail "stage scripts: ${bad[*]}"
}
