@echo off
python -m psycheval.harbor.verifier "%~dp0grader.json"
exit /b %ERRORLEVEL%
