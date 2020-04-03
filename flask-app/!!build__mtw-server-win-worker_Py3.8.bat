@echo off
setlocal
echo.
set python=c:\Programs\Python\Python38\Scripts\pyinstaller.exe
echo Build using pyinstaller : %python%
set targetDir=dist
set fileHandle=mtw-server-win-worker
set srcFile=%fileHandle%.py
set srcDir=mtw
set logFile=!build_%fileHandle%.rep

echo. > %logFile%

echo.
echo rem call %targetDir%\%fileHandle%.exe stop

echo.
echo Building %srcFile% ...

CALL %python% --log-level ERROR --onefile ^
              --hidden-import=_cffi_backend --hidden-import=pkg_resources.py2_warn --hidden-import=tornado ^
              --add-data mtw_utils/pyuca/*.txt;pyuca ^
              --distpath %targetDir% %srcFile% >> %logFile% 2>&1

echo  - Done!


echo.
echo rem call %targetDir%\%fileHandle%.exe install
echo.
echo rem call %targetDir%\%fileHandle%.exe start

echo Finished
echo.

endlocal
