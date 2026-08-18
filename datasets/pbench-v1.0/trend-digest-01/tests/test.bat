@echo off
setlocal
set "tests_dir=%~dp0"
echo psycheval-test-entrypoint=bat
python "%tests_dir%verify.py" "%tests_dir%grader.json"
set "exit_code=%ERRORLEVEL%"
endlocal & exit /b %exit_code%
