@echo off
setlocal
echo.
echo Build using pyinstaller
set targetDir=dist
set fileHandle=mesh-nt2trx
set srcFile=%fileHandle%.py
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo Building %srcFile% ...

CALL c:\Python37\Scripts\pyinstaller.exe --log-level ERROR --onefile --distpath %targetDir% %srcFile% >> %logFile% 2>&1

set fileHandle=mesh-xml2trx
set srcFile=%fileHandle%.py
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo Building %srcFile% ...

CALL c:\Python37\Scripts\pyinstaller.exe --log-level ERROR --onefile --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo.
echo Finished
echo.

endlocal
