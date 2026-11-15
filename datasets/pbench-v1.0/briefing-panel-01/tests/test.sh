#!/bin/sh
set -eu
tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python -m psycheval.harbor.verifier "$tests_dir/grader.json"
