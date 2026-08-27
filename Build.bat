@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher ^(py.exe^) was not found.
    exit /b 1
)

py -3.11 -c "import sys; a=sys.version_info[:3]; sys.exit(0 if a==(3,11,9) else f'ERROR: Python 3.11.9 is required; found {a[0]}.{a[1]}.{a[2]}')"
if errorlevel 1 exit /b 1

py -3.11 -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 exit /b 1

py -3.11 -m py_compile setup_tool.py setup_tool_dynamic.py remote_packages.py tests/test_safety.py
if errorlevel 1 exit /b 1

py -3.11 -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

py -3.11 -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --icon=PurpleWowLogo.ico ^
    --add-data "PurpleWowLogo.ico;." ^
    --add-data "Payload;Payload" ^
    --add-data "vanilla-tweaks.exe;." ^
    --name "WoW_Modernization_Tool" ^
    setup_tool_dynamic.py
if errorlevel 1 exit /b 1

if not exist "dist\WoW_Modernization_Tool.exe" (
    echo ERROR: Build output is missing.
    exit /b 1
)

echo Build complete: dist\WoW_Modernization_Tool.exe
