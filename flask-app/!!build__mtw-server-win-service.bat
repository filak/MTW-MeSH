@echo off
setlocal
echo.
echo Build using pyinstaller
set targetDir=dist
set fileHandle=mtw-server-win-service
set srcFile=%fileHandle%.py
set srcDir=mtw
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo rem call %targetDir%\%fileHandle%.exe stop

echo.
echo Building %srcFile% ...

CALL c:\Python37\Scripts\pyinstaller.exe --log-level ERROR --onefile --hidden-import=_cffi_backend --add-data mtw_utils/pyuca/*.txt;pyuca --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo  - Done!
echo.
echo Cleaning static files %targetDir% ...

RMDIR %targetDir%\static /S /Q
RMDIR %targetDir%\templates /S /Q

echo  - Done!
echo.
echo Copying files...

MKDIR %targetDir%\static
xcopy %srcDir%\static %targetDir%\static /E /Q /Y
MKDIR %targetDir%\templates
xcopy %srcDir%\templates %targetDir%\templates /E /Q /Y
echo  - Done!
echo.

echo.
echo rem call %targetDir%\%fileHandle%.exe install
echo.
echo rem call %targetDir%\%fileHandle%.exe start

echo Finished
echo.

endlocal
