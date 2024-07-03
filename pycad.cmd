@echo off
call .venv\Scripts\activate.bat
start "python" "%~dp0\pycad\main.py" %*