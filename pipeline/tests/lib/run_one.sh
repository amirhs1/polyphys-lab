#!/usr/bin/env bash
# Runs one test function in a fresh process and sandbox.
#
# Called by run_tests.sh, not by hand: run_one.sh TEST_FILE TEST_FUNCTION
#
# Each test gets its own process because `set -e` is ignored inside a
# function whose status `if`, `&&`, or `||` tests; a separate process keeps
# errexit meaningful inside the test.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=helpers.sh
source "${here}/helpers.sh"
# shellcheck disable=SC1090  # the test file is chosen at run time
source "$1"

_setup
"$2"
