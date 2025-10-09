@echo off
echo ========================================
echo   Rust AFK Hour Adder - Startup Setup
echo ========================================
echo.

REM Get the current directory (where this batch file is located)
set "SCRIPT_DIR=%~dp0"
set "MAIN_DIR=%SCRIPT_DIR%.."
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo Script directory: %SCRIPT_DIR%
echo Main directory: %MAIN_DIR%
echo Startup directory: %STARTUP_DIR%
echo.

REM Check if the main Python script exists
if not exist "%MAIN_DIR%\rust_battlemetrics_hour_adder.py" (
    echo ERROR: rust_battlemetrics_hour_adder.py not found!
    echo Expected location: %MAIN_DIR%\rust_battlemetrics_hour_adder.py
    echo.
    pause
    exit /b 1
)

echo Found Python script: %MAIN_DIR%\rust_battlemetrics_hour_adder.py
echo.

REM Create the startup batch file
echo Creating startup batch file...
(
echo @echo off
echo echo Starting Rust AFK Hour Adder from Windows Startup...
echo echo.
echo cd /d "%MAIN_DIR%"
echo if not exist "rust_battlemetrics_hour_adder.py" ^(
echo     echo ERROR: Script not found in %%cd%%
echo     pause
echo     exit /b 1
echo ^)
echo python rust_battlemetrics_hour_adder.py
echo if errorlevel 1 ^(
echo     echo Error starting the script. Press any key to exit.
echo     pause
echo ^)
) > "%STARTUP_DIR%\rust_afk_startup.bat"

if exist "%STARTUP_DIR%\rust_afk_startup.bat" (
    echo SUCCESS: Startup file created at:
    echo %STARTUP_DIR%\rust_afk_startup.bat
    echo.
    echo The Rust AFK Hour Adder will now start automatically when Windows boots.
    echo Make sure to enable "Start farming at Windows startup" in the app settings.
) else (
    echo ERROR: Failed to create startup file.
    echo You may need to run this as administrator.
)

echo.
echo Setup complete!
pause