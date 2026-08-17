@echo off
REM Lanzador para actualizar_github.ps1 sin depender de la politica de ejecucion
REM ni de la marca "descargado de internet" de Windows. Solo dale doble clic.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0actualizar_github.ps1"
pause
