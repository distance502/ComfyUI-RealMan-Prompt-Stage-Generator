@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "NODE_DIR=%~dp0"
if "%NODE_DIR:~-1%"=="\" set "NODE_DIR=%NODE_DIR:~0,-1%"

set "COMFY_ROOT="
if not "%~1"=="" call :TryComfyRoot "%~1"
if "%~1"=="" call :TryComfyRoot "%NODE_DIR%\..\.."

echo.
echo 真男人提示词阶段生成器 - 内嵌安装到 ComfyUI
echo 当前节点目录:
echo   "%NODE_DIR%"
echo.

if not defined COMFY_ROOT (
    echo [提示] 没有识别到有效的 ComfyUI 根目录。
    echo [提示] 请输入或拖入包含 folder_paths.py / main.py 的 ComfyUI 文件夹。
    echo.
    call :PromptForComfyRoot
)

if not defined COMFY_ROOT (
    echo.
    echo [失败] 这个目录不是有效的 ComfyUI 根目录:
    echo   "%COMFY_ROOT%"
    echo.
    pause
    exit /b 1
)

if not exist "%NODE_DIR%\embed_into_comfyui.py" (
    echo.
    echo [失败] 找不到安装脚本:
    echo   "%NODE_DIR%\embed_into_comfyui.py"
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD="
set "PYTHON_ARGS="
call :TryPython "%COMFY_ROOT%\..\python_embeded\python.exe"
call :TryPython "%COMFY_ROOT%\python_embeded\python.exe"
call :TryPython "%COMFY_ROOT%\.venv\Scripts\python.exe"
call :TryPython "%COMFY_ROOT%\venv\Scripts\python.exe"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py"
        set "PYTHON_ARGS=-3"
    )
)

if not defined PYTHON_CMD (
    echo.
    echo [失败] 没找到可用 Python。
    echo [提示] 便携版通常在 ComfyUI 上一级 python_embeded\python.exe。
    echo.
    pause
    exit /b 1
)

echo [信息] 使用 ComfyUI 根目录:
echo   "%COMFY_ROOT%"
echo [信息] 使用 Python:
echo   "%PYTHON_CMD%" %PYTHON_ARGS%
echo [信息] 即将复制当前节点到:
echo   "%COMFY_ROOT%\custom_nodes\ComfyUI-RealMan-Prompt-Stage-Generator"
echo.

pushd "%COMFY_ROOT%" >nul
if errorlevel 1 (
    echo [失败] 无法进入 ComfyUI 根目录:
    echo   "%COMFY_ROOT%"
    echo.
    pause
    exit /b 1
)

"%PYTHON_CMD%" %PYTHON_ARGS% "%NODE_DIR%\embed_into_comfyui.py" "%COMFY_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
popd

echo.
if "%EXIT_CODE%"=="0" (
    echo [完成] 内嵌安装完成。
    echo [下一步] 请重启 ComfyUI，并在浏览器 Ctrl+F5 强制刷新。
) else (
    echo [失败] 内嵌安装没有完成，请把上面的输出发回来。
)
echo.
pause
exit /b %EXIT_CODE%

:TryComfyRoot
if defined COMFY_ROOT goto :eof
if exist "%~1\folder_paths.py" set "COMFY_ROOT=%~f1"
goto :eof

:PromptForComfyRoot
set "USER_COMFY_ROOT="
set /p "USER_COMFY_ROOT=ComfyUI 根目录: "
set "USER_COMFY_ROOT=%USER_COMFY_ROOT:"=%"
call :TryComfyRoot "%USER_COMFY_ROOT%"
goto :eof

:TryPython
if defined PYTHON_CMD goto :eof
if exist "%~1" set "PYTHON_CMD=%~f1"
goto :eof
