# shellcheck shell=bash
# Tests of the harness itself: each runs the lab under test's own
# run_tests.sh on a test file it builds, so a fault planted in a copy's
# harness is caught by this tree's.

# shellcheck disable=SC2034  # STATUS is read by assert_status, in lib/helpers.sh
_run_harness() { # _run_harness FILE: run the harness on FILE alone
    STATUS=0
    "${BASH}" "${LAB_TEST_ROOT}/pipeline/tests/run_tests.sh" --root "${LAB_TEST_ROOT}" "$1" \
        >"${T}/out" 2>"${T}/err" || STATUS=$?
}

# The harness counts a passed, a failed, and a skipped test, and exits 1
# only while a test fails.
test_harness_reports_a_failure() {
    mkdir -p "${T}/fake"
    cat >"${T}/fake/test_fake.sh" <<'EOF'
test_passes() { :; }
test_fails() { fail "planted"; }
test_skips() { skip "planted"; }
EOF
    _run_harness "${T}/fake/test_fake.sh"
    assert_status 1
    assert_match "${T}/out" '^passed: 1   failed: 1   skipped: 1$'
    assert_match "${T}/out" 'FAIL  test_fails'
    sed -i.bak '/test_fails/d' "${T}/fake/test_fake.sh"
    _run_harness "${T}/fake/test_fake.sh"
    assert_status 0
    assert_match "${T}/out" '^passed: 1   failed: 0   skipped: 1$'
}

# Each test gets its own sandbox and home folder, with the cluster
# commands stubbed first on PATH.
test_harness_isolates_each_test() {
    mkdir -p "${T}/fake"
    cat >"${T}/fake/test_fake.sh" <<'EOF'
test_a_writes() {
    sbatch job.sh
    [[ -n "$(stub_calls sbatch)" ]] || fail "sbatch reached no stub"
    : >"${HOME}/marker"
}
test_b_sees_nothing() {
    [[ ! -e "${HOME}/marker" ]] || fail "home folder shared"
    [[ -z "$(stub_calls sbatch)" ]] || fail "stub log shared"
}
EOF
    _run_harness "${T}/fake/test_fake.sh"
    assert_status 0
    assert_match "${T}/out" '^passed: 2   failed: 0   skipped: 0$'
    assert_not_called sbatch "the outer sandbox's stub"
}
