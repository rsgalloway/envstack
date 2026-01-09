@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =============================================================================
rem Project: EnvStack - Environment Variable Management
rem make.bat - Windows-friendly Makefile target runner
rem
rem Usage:
rem   make.bat                -> build
rem   make.bat clean          -> remove build artifacts
rem   make.bat test           -> run basic envstack shell checks
rem   make.bat dryrun         -> simulate installation (dist --dryrun)
rem   make.bat install        -> build then dist --force --yes
rem   make.bat help           -> show this help
rem =============================================================================

set "BUILD_DIR=build"
set "ENVPATH=%CD%\env"
set "ENVSTACK_CMD=envstack"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=build"

if /I "%TARGET%"=="help"   goto :help
if /I "%TARGET%"=="clean"  goto :clean
if /I "%TARGET%"=="build"  goto :build
if /I "%TARGET%"=="all"    goto :build
if /I "%TARGET%"=="test"   goto :test
if /I "%TARGET%"=="dryrun" goto :dryrun
if /I "%TARGET%"=="install" goto :install

echo.
echo Unknown target: "%TARGET%"
echo.
goto :help

:help
echo Targets:
echo   build    - Build artifacts (pip install -r requirements.txt -t %BUILD_DIR%)
echo   clean    - Remove build artifacts (%BUILD_DIR%)
echo   test     - Basic envstack command checks
echo   dryrun   - Simulate installation (dist --dryrun) via envstack
echo   install  - Build then install using distman (dist --force --yes)
echo   all      - Alias for build
echo   help     - Show this help
echo.
echo Notes:
echo   - ENVPATH is set to: %ENVPATH%
echo   - Requires: python/pip, envstack, and distman (for dryrun/install)
exit /b 0

:clean
echo [clean] Removing "%BUILD_DIR%" ...
if exist "%BUILD_DIR%" (
  rmdir /s /q "%BUILD_DIR%"
)
exit /b 0

:build
call :clean || exit /b 1
echo [build] Installing requirements into "%BUILD_DIR%" ...
python -m pip install -r requirements.txt -t "%BUILD_DIR%"
if errorlevel 1 exit /b 1
exit /b 0

:test
echo [test] Running envstack checks...
rem Use a one-liner so ENVPATH applies to the envstack process.
set "CMD=set ENVPATH=%ENVPATH% ^&^& %ENVSTACK_CMD% -- dir"
cmd /c "%CMD%"
if errorlevel 1 exit /b 1

set "CMD=set ENVPATH=%ENVPATH% ^&^& %ENVSTACK_CMD% -- where python"
cmd /c "%CMD%"
if errorlevel 1 exit /b 1

exit /b 0

:dryrun
echo [dryrun] Simulating install via dist --dryrun...
set "CMD=set ENVPATH=%ENVPATH% ^&^& %ENVSTACK_CMD% -- dist --dryrun"
cmd /c "%CMD%"
exit /b %errorlevel%

:install
call :build || exit /b 1
echo [install] Installing via distman (dist --force --yes)...
dist --force --yes
exit /b %errorlevel%