@echo off
setlocal
echo.
echo Build using pyinstaller
set targetDir=dist
set fileHandle=mtw-server-win-worker
set srcFile=%fileHandle%.py
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo rem call %targetDir%\%fileHandle%.exe stop

echo.
echo Building %srcFile% ...

CALL c:\Python37\Scripts\pyinstaller.exe --log-level ERROR --onefile --add-data mtw_utils/pyuca/*.txt;pyuca --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo  - Done!


echo.
echo rem call %targetDir%\%fileHandle%.exe install
echo.
echo rem call %targetDir%\%fileHandle%.exe start

echo Finished
echo.

endlocal
