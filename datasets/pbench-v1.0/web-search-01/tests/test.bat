@echo off
setlocal
if defined PSYCHEVAL_TESTS_DIR (set "tests_dir=%PSYCHEVAL_TESTS_DIR%") else (set "tests_dir=C:\tests")
if defined PSYCHEVAL_HARBOR_PYTHON (set "python_bin=%PSYCHEVAL_HARBOR_PYTHON%") else (set "python_bin=python")
echo psycheval-test-entrypoint=bat
"%python_bin%" -m psycheval.harbor.verifier "%tests_dir%\grader.json"
set "exit_code=%ERRORLEVEL%"
endlocal & exit /b %exit_code%
