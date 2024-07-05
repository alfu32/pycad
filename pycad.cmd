@echo off

echo "%~dp0.venv\Scripts\activate.bat"
call "%~dp0.venv\Scripts\activate.bat"

echo "%~dp0pycad\main.py"
start "python" "%~dp0pycad\main.py" %*

deactivate
pause