@echo off
cd /d "%~dp0.."
.venv\Scripts\pytest tests\ -v %*
