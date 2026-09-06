@echo off
call "C:\oneAPI\oneAPI\setvars.bat" intel64 >nul 2>nul
if errorlevel 1 exit /b %errorlevel%
cd /d "%~dp0.."
%*
