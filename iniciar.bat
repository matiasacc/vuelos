@echo off
cd /d "%~dp0"
title Pantalla de vuelos
python --version >nul 2>nul
if %errorlevel%==0 (python servidor_vuelos.py) else (py servidor_vuelos.py)
pause
