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

:: 0b. Real JASS parse/type gate against the installed Warcraft III natives.
set "WC3_ROOT=%~dp0..\..\..\"
"%WC3_ROOT%jasshelper\pjass.exe" "%WC3_ROOT%jasshelper\common.j" "%WC3_ROOT%jasshelper\Blizzard.j" "src\war3map.j"
if errorlevel 1 (
    echo BUILD ABORTED: pjass compilation failed.
    if not "%1"=="nopause" pause
    exit /b 1
)

:: 1. Copy the clean terrain/shell map to the distribution folder
copy /Y "base_map.w3x" "dist\Tides_of_War_Compiled.w3x"
if errorlevel 1 (
    echo BUILD ABORTED: dist\Tides_of_War_Compiled.w3x is locked.
    echo Close Warcraft III or any archive viewer using the map, then rebuild.
    if not "%1"=="nopause" pause
    exit /b 1
)

:: 2. Rebuild presentation object data for custom hero overhauls.
::    base_map.w3x remains immutable; the patched file only enters dist.
if not exist "build\objectdata" mkdir "build\objectdata"
if not exist "build\patched" mkdir "build\patched"
MPQEditor.exe extract "base_map.w3x" "war3map.w3a" "build\objectdata"
MPQEditor.exe extract "base_map.w3x" "war3map.w3u" "build\objectdata"
python scripts\patch_tiles_object_data.py "build\objectdata\war3map.w3a" "build\patched\war3map.w3a" --unit-input "build\objectdata\war3map.w3u" --unit-output "build\patched\war3map.w3u"
if errorlevel 1 (
    echo BUILD ABORTED: object-data patch failed.
    if not "%1"=="nopause" pause
    exit /b 1
)

:: 3. Inject the external script and patched ability presentation data.
:: Delete GUI trigger files so World Editor / WC3 engine does not override war3map.j
MPQEditor.exe delete "dist\Tides_of_War_Compiled.w3x" "war3map.wtg"
MPQEditor.exe delete "dist\Tides_of_War_Compiled.w3x" "war3map.wct"
MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "war3map.j"
if errorlevel 1 exit /b 1
timeout /t 1 /nobreak >nul 2>&1
MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "scripts\war3map.j"
if errorlevel 1 exit /b 1
timeout /t 1 /nobreak >nul 2>&1
MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "build\patched\war3map.w3a" "war3map.w3a"
if errorlevel 1 exit /b 1
timeout /t 1 /nobreak >nul 2>&1
MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "build\patched\war3map.w3u" "war3map.w3u"
if errorlevel 1 exit /b 1

echo.
echo Build Successful! Map generated in \dist folder.
if not "%1"=="nopause" pause
