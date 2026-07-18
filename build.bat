@echo off
echo ==========================================
echo       BUILDING TIDES OF WAR...
echo ==========================================

:: 0. Static validation gates - build FAILS if the script is broken or leaks regressed
python .agents\skills\warcraft3-jass-optimization\scripts\validate_jass_syntax.py src\war3map.j
if errorlevel 1 (
    echo BUILD ABORTED: JASS validation failed.
    if not "%1"=="nopause" pause
    exit /b 1
)

:: 1. Copy the clean terrain/shell map to the distribution folder
copy /Y "base_map.w3x" "dist\Tides_of_War_Compiled.w3x"

:: 2. Inject your external script (which contains all old + new code) into the map
MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "war3map.j"

echo.
echo Build Successful! Map generated in \dist folder.
if not "%1"=="nopause" pause
