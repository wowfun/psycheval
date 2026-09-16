@echo off
setlocal
python -m psycheval.harbor.verifier "%~dp0grader.json"
set "exit_code=%ERRORLEVEL%"
endlocal & exit /b %exit_code%
