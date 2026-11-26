#!/usr/bin/env bash
# The shell test harness of the pipeline.
#
# Runs every test_* function of pipeline/tests/test_*.sh, each in its own
# bash process and its own throwaway sandbox, with the cluster commands
# replaced by logging stubs. It needs no cluster and no SLURM.
#
# Usage, from the repository root:
#   bash pipeline/tests/run_tests.sh [-v] [-k PATTERN] [--root DIR] [FILE...]
#
#   -v          show the output of every test, not only of failed ones
#   -k PATTERN  run only the tests whose name contains PATTERN
#   --root DIR  test the lab at DIR, a copy, instead of this one; the tests
#               are still this tree's (how a test is shown to fail)
#   FILE        run only these test files (default: tests/test_*.sh)
#
# Exit status: 0 when no test failed (skips are not failures), 1 when one
# did, 2 on misuse.

# Written in bash 3.2 syntax up to the version check, so an old bash
# reaches it.
if [ -z "${BASH_VERSINFO[0]:-}" ] || [ "${BASH_VERSINFO[0]}" -lt 4 ] ||
    { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -lt 4 ]; }; then
    echo "run_tests.sh: bash ${BASH_VERSION:-unknown} found; 4.4 or later is needed." >&2
    echo "On macOS, put Homebrew's bash first on PATH, or run it with that bash." >&2
    exit 2
fi
set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
    echo "run_tests.sh: do not run the harness as root." >&2
    exit 2
fi

tests_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
root="$(cd "${tests_dir}/../.." && pwd -P)"

usage() {
    sed -n '2,/^# did, 2 on misuse/{s/^# \{0,1\}//;p;}' "${BASH_SOURCE[0]}"
    exit "${1:-0}"
}

verbose="" filter="" files=()
while (($#)); do
    case "$1" in
        -h | --help) usage 0 ;;
        -v) verbose=1 ;;
        -k)
            filter="${2:?-k needs a pattern}"
            shift
            ;;
        --root)
            root="$(cd "${2:?--root needs a folder}" && pwd -P)" || exit 2
            shift
            ;;
        -*)
            echo "run_tests.sh: unknown option: $1" >&2
            usage 2
            ;;
        *) files+=("$1") ;;
    esac
    shift
done

if [[ ! -f "${root}/pipeline/lib/common.sh" ]]; then
    echo "run_tests.sh: no pipeline/lib/common.sh under ${root}" >&2
    exit 2
fi
if ((${#files[@]} == 0)); then
    files=("${tests_dir}"/test_*.sh)
fi

export LAB_TEST_ROOT="${root}"
export LAB_TEST_VERBOSE="${verbose}"

logs="$(mktemp -d "${TMPDIR:-/tmp}/lab-harness.XXXXXX")"
trap 'rm -rf -- "${logs:?}"' EXIT

passed=0 failed=0 skipped=0 failures=()
for file in "${files[@]}"; do
    if [[ ! -f "${file}" ]]; then
        echo "run_tests.sh: no such test file: ${file}" >&2
        exit 2
    fi
    # shellcheck disable=SC2016  # expanded by the child bash, not here
    mapfile -t tests < <("${BASH}" -c 'source "$1" && compgen -A function test_ || true' _ "${file}")
    printf '%s\n' "${file##*/}"
    for t in "${tests[@]}"; do
        [[ -z "${filter}" || "${t}" == *"${filter}"* ]] || continue
        log="${logs}/${t}.log"
        status=0
        "${BASH}" "${tests_dir}/lib/run_one.sh" "${file}" "${t}" >"${log}" 2>&1 ||
            status=$?
        case "${status}" in
            0)
                passed=$((passed + 1))
                printf '  ok    %s\n' "${t}"
                ;;
            77)
                skipped=$((skipped + 1))
                printf '  skip  %s  (%s)\n' "${t}" "$(sed -n 's/^SKIP: //p' "${log}" | head -n 1)"
                ;;
            *)
                failed=$((failed + 1))
                failures+=("${file##*/}::${t}")
                printf '  FAIL  %s\n' "${t}"
                sed 's/^/        | /' "${log}"
                ;;
        esac
        if [[ -n "${verbose}" && ("${status}" -eq 0 || "${status}" -eq 77) ]]; then
            sed 's/^/        | /' "${log}"
        fi
    done
done

echo "---------------------------------------"
printf 'passed: %d   failed: %d   skipped: %d\n' "${passed}" "${failed}" "${skipped}"
if ((failed)); then
    printf '  %s\n' "${failures[@]}"
    exit 1
fi
