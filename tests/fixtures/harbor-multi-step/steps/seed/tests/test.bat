@echo off
setlocal
set "tests_dir=%~dp0"
python -m psycheval.harbor.verifier "%tests_dir%grader.json"
set "exit_code=%ERRORLEVEL%"
endlocal & exit /b %exit_code%
