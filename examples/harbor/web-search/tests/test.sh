#!/bin/sh
set -eu

tests_dir=${PSYCHEVAL_TESTS_DIR:-/tests}
python_bin=${PSYCHEVAL_HARBOR_PYTHON:-python3}
"$python_bin" -m psycheval_harbor.verifier "$tests_dir/grader.json"
