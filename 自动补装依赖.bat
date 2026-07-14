@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "COMFY_ROOT="
set "PYTHON_CMD="
set "PYTHON_ARGS="

echo [QwenTE] Optional dependency installer
echo.

if not "%~1"=="" call :TryComfyRoot "%~1"
call :TryComfyRoot "%SCRIPT_DIR%..\.."
if not defined COMFY_ROOT (
    echo [INFO] Could not auto-detect the ComfyUI root from this folder.
    set "USER_COMFY_ROOT="
    set /p "USER_COMFY_ROOT=Type or drag the ComfyUI folder here, then press Enter: "
    set "USER_COMFY_ROOT=%USER_COMFY_ROOT:"=%"
    call :TryComfyRoot "%USER_COMFY_ROOT%"
)

if not defined COMFY_ROOT (
    echo [ERROR] No valid ComfyUI root was provided. folder_paths.py was not found.
    pause
    exit /b 1
)

call :TryPython "%COMFY_ROOT%\..\python_embeded\python.exe"
call :TryPython "%COMFY_ROOT%\python_embeded\python.exe"
call :TryPython "%COMFY_ROOT%\.venv\Scripts\python.exe"
call :TryPython "%COMFY_ROOT%\venv\Scripts\python.exe"

if not defined PYTHON_CMD (
    for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYTHON_CMD set "PYTHON_CMD=%%I"
)
if not defined PYTHON_CMD (
    for /f "delims=" %%I in ('where py 2^>nul') do if not defined PYTHON_CMD (
        set "PYTHON_CMD=%%I"
        set "PYTHON_ARGS=-3"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python was not found.
    echo [INFO] Portable ComfyUI usually has python_embeded\python.exe next to the ComfyUI folder.
    echo [INFO] You can also run install_dependencies.py with your ComfyUI Python manually.
    pause
    exit /b 1
)

echo [INFO] ComfyUI root: %COMFY_ROOT%
echo [INFO] Python: %PYTHON_CMD% %PYTHON_ARGS%
echo.
echo [INFO] This installs optional dependencies for quality audit and local GGUF features.
echo [INFO] The main node UI can still load even if optional packages fail to install.
echo.

"%PYTHON_CMD%" %PYTHON_ARGS% "%SCRIPT_DIR%install_dependencies.py" "%COMFY_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo [DONE] Optional dependency install finished.
) else (
    echo [DONE] Installer finished with issues to review.
)
pause
exit /b %EXIT_CODE%

:TryComfyRoot
if defined COMFY_ROOT goto :eof
if exist "%~1\folder_paths.py" set "COMFY_ROOT=%~f1"
goto :eof

:TryPython
if defined PYTHON_CMD goto :eof
if exist "%~1" set "PYTHON_CMD=%~f1"
goto :eof
