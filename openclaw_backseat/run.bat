@echo off
REM ---------------------------------------------------------------------------
REM run.bat - thin wrapper OpenClaw (or you) can call to launch the pipeline.
REM Usage:  run.bat "Modern Villa" architecture
REM         run.bat "Lamborghini" automotive --flagship
REM Asset defaults to the newest accepted file in pipeline\hot_folder.
REM ---------------------------------------------------------------------------
setlocal
set "BLKK_SITE=C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
cd /d "%BLKK_SITE%"

set "PROJECT=%~1"
set "CATEGORY=%~2"
set "EXTRA=%~3"

if "%PROJECT%"=="" (
  echo Usage: run.bat "Project Name" [architecture^|automotive] [--flagship]
  exit /b 1
)

set "CATFLAG="
if not "%CATEGORY%"=="" set "CATFLAG=--category %CATEGORY%"

python pipeline\run_pipeline.py --project-name "%PROJECT%" %CATFLAG% %EXTRA%
endlocal
