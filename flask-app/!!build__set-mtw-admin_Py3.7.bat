@echo off
setlocal
echo.
set python=c:\Python37\Scripts\pyinstaller.exe
echo Build using pyinstaller : %python%
set targetDir=dist
set fileHandle=set-mtw-admin
set srcFile=%fileHandle%.py
set srcDir=mtw
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo Building %srcFile% ...

CALL %python% --log-level ERROR --onefile ^
              --hidden-import=_cffi_backend --hidden-import=pkg_resources.py2_warn ^
              --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo.
echo Finished
echo.

endlocal