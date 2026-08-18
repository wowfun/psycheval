#!/bin/sh
set -eu

tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
printf '%s\n' 'psycheval-test-entrypoint=sh'
python "$tests_dir/verify.py" "$tests_dir/grader.json"
