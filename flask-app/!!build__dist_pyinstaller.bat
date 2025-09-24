@echo off
setlocal
echo.
set python=venv\Scripts\pyinstaller.exe

echo.
choice /C AN /M "Activate Python VENV ?  A/N"
if errorlevel 2 goto:start

echo.
echo Activating VENV
call venv\Scripts\activate

:start
echo.
choice /C AN /M "Clean build ?  A/N"
if errorlevel 1 set buildClean=--clean
if errorlevel 2 set buildClean=

choice /C AN /M "Test run ?  A/N"
if errorlevel 1 set testRun=1
if errorlevel 2 set testRun=0

echo Build using pyinstaller : %python%

set srcDir=application
set targetDir=dist
set subdir=
set logFile=!build_dist_pyinstaller.rep

echo.
echo Cleaning static files %targetDir% ...
RMDIR %targetDir%\static /S /Q
RMDIR %targetDir%\templates /S /Q

echo.
echo Copying files from: static, templates ...
xcopy %srcDir%\static %targetDir%\static /I /E /Q /Y
xcopy %srcDir%\templates %targetDir%\templates /I /E /Q /Y

echo. > %logFile%

set fileHandle=mtw-server
set extras=--add-data %srcDir%/pyuca/*.txt;pyuca
set subdir=
call:buildFiles

set fileHandle=mtw-worker
set extras=--add-data %srcDir%/pyuca/*.txt;pyuca
set subdir=
call:buildFiles

set fileHandle=set-mtw-admin
set extras=
set subdir=
call:buildFiles

set fileHandle=mesh-extract-deleted
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=mesh-get-inactive
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=mesh-nt2trx
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=mesh-trx2nt
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=mesh-xml2trx
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=update-ns
set extras=
set subdir=tools\
call:buildFiles

set fileHandle=secrets-gen
set extras=
set subdir=tools\
call:buildFiles

echo.
echo Finished !!!
echo.

title Finished building!
goto:eof

:buildFiles
set srcFile=%subdir%%fileHandle%.py
echo.
echo Building %srcFile%
title Building %srcFile%

CALL %python% --log-level ERROR --onefile %extras% --distpath %targetDir%\%subdir% %srcFile% %buildClean% >> %logFile% 2>&1

if %testRun%==1 call:runTestHelp
goto:eof

:runTestHelp
echo.
set binFile=%subdir%%fileHandle%.exe
echo Running %targetDir%\%binFile% ...
CALL %targetDir%\%binFile% -h
echo.
echo Done.
echo.
goto:eof

endlocal

