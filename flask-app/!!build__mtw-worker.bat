@echo off
setlocal
echo.
REM set python=c:\Programs\Python\Python38\Scripts\pyinstaller.exe
set python=venv\Scripts\pyinstaller.exe
echo Build using pyinstaller : %python%
set targetDir=dist
set fileHandle=mtw-worker
set srcFile=%fileHandle%.py
set srcDir=application
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo Stop the service:  %targetDir%\%fileHandle%.exe

echo.
echo Building %srcFile% ...

CALL %python% --log-level ERROR --onefile ^
              --add-data %srcDir%/pyuca/*.txt;pyuca ^
              --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo  - Done!
echo.

echo.
echo Finished
echo.

endlocal
