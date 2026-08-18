#!/bin/sh
set -eu

tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
printf '%s\n' 'psycheval-test-entrypoint=sh'
python -m psycheval.harbor.verifier "$tests_dir/grader.json"
