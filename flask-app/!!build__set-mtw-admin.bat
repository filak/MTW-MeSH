@echo off
setlocal
echo.
REM set python=c:\Programs\Python\Python38\Scripts\pyinstaller.exe
set python=venv\Scripts\pyinstaller.exe
echo Build using pyinstaller : %python%

echo.
choice /C AN /M "Activate Python VENV ?  A/N"
if errorlevel 2 goto:start

echo.
echo Activating VENV
call venv\Scripts\activate

:start
set targetDir=dist
set fileHandle=set-mtw-admin
set srcFile=%fileHandle%.py
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo Building %srcFile% ...

CALL %python% --log-level ERROR --onefile --clean ^
              --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo.
echo Finished
echo.

endlocal
