@echo off
rem psycheval-test-entrypoint=python-verifier
python -m psycheval.harbor.verifier "%~dp0grader.json"
exit /b %ERRORLEVEL%
