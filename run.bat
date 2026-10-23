@echo off
chcp 936 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM GameDie 一键启动 + 环境自动检测 + CSGO 自动配置
REM 双击运行即可：
REM   1. 自动检测并安装所需环境（Python 依赖 / 前端依赖）
REM   2. 自动定位 CS2/CSGO 安装目录，写入 autoexec.cfg 开启日志
REM   3. 后台最小化启动 后端 + Agent + 前端
REM   4. 自动打开看板（浏览器）
REM   5. 弹出实时监控窗口，持续显示 Agent 日志与 CSGO 日志状态
REM
REM 前置条件：需已安装 Python 3.10+ 和 Node.js 18+（已加入 PATH）
REM 关闭全部服务：关闭弹出的 4 个窗口即可
REM   (Backend / Agent / Frontend / Monitor)
REM ============================================================

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "AGENT_DIR=%ROOT%agent"
set "FRONTEND_DIR=%ROOT%frontend"
set "SETUP_PS1=%ROOT%scripts\setup-csgo.ps1"
set "MONITOR_PS1=%ROOT%scripts\monitor.ps1"

echo.
echo  ============================================================
echo   GameDie 一键启动 + 环境自动检测
echo  ============================================================
echo.

REM ---- 0. 基础环境自检 ----
echo [0/5] 检查基础环境...
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 python，请先安装 Python 3.10+ 并加入 PATH。
    echo        下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 npm，请先安装 Node.js 18+ 并加入 PATH。
    echo        下载地址: https://nodejs.org/
    pause
    exit /b 1
)
echo       [OK] python / npm 已就绪
echo.

REM ---- 1. 后端 Python 依赖检测与安装 ----
echo [1/5] 检查后端 Python 依赖...
python -c "import fastapi, uvicorn, pydantic, dateutil" >nul 2>nul
if errorlevel 1 (
    echo       [缺失] 正在安装后端依赖...
    python -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if errorlevel 1 (
        echo [错误] 后端依赖安装失败，请手动执行: python -m pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
    echo       [OK] 后端依赖安装完成
) else (
    echo       [OK] 后端依赖已就绪
)
echo.

REM ---- 2. Agent Python 依赖检测与安装 ----
echo [2/5] 检查 Agent Python 依赖...
python -c "import psutil, requests, dateutil, pycaw, comtypes" >nul 2>nul
if errorlevel 1 (
    echo       [缺失] 正在安装 Agent 依赖...
    python -m pip install -r "%AGENT_DIR%\requirements.txt"
    if errorlevel 1 (
        echo [错误] Agent 依赖安装失败，请手动执行: python -m pip install -r agent\requirements.txt
        pause
        exit /b 1
    )
    echo       [OK] Agent 依赖安装完成
) else (
    echo       [OK] Agent 依赖已就绪
)
echo.

REM ---- 3. 前端依赖检测与安装 ----
echo [3/5] 检查前端依赖...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo       [缺失] 正在安装前端依赖（首次较慢，请耐心等待）...
    call npm --prefix "%FRONTEND_DIR%" install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败，请手动执行: npm --prefix frontend install
        pause
        exit /b 1
    )
    echo       [OK] 前端依赖安装完成
) else (
    echo       [OK] 前端依赖已就绪
)
echo.

REM ---- 4. 自动配置 CSGO ----
echo [4/5] 自动配置 CSGO (定位游戏目录 + 写入 autoexec.cfg)...
if exist "%SETUP_PS1%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SETUP_PS1%"
    if errorlevel 3 (
        echo.
        echo       [警告] 配置过程出现错误，CSGO 死亡识别可能无法工作。
        echo              其他功能（看板、数据统计）仍可正常使用。
        echo.
    ) else if errorlevel 2 (
        echo.
        echo       [提示] 未找到 CS2/CSGO 安装目录，CSGO 死亡识别将无法工作。
        echo              其他功能（看板、数据统计）仍可正常使用。
        echo.
    )
) else (
    echo       [警告] 未找到 scripts\setup-csgo.ps1，跳过 CSGO 自动配置。
)
echo.

REM ---- 5. 启动服务 ----
echo [5/5] 启动服务...
echo        启动后端 (端口 8000)...
start "GameDie Backend" /MIN cmd /k "cd /d %BACKEND_DIR% && python main.py"
timeout /t 2 /nobreak >nul

echo        启动 Agent...
start "GameDie Agent" /MIN cmd /k "cd /d %AGENT_DIR% && python main.py"
timeout /t 1 /nobreak >nul

echo        启动前端看板 (端口 5173)...
start "GameDie Frontend" /MIN cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo  ============================================================
echo   全部已启动（最小化运行中）
echo  ============================================================
echo   后端 API:   http://localhost:8000
echo   看板:        http://localhost:5173
echo  ============================================================
echo.
echo  等待前端就绪...
timeout /t 5 /nobreak >nul

echo  正在打开看板...
start http://localhost:5173

echo  正在弹出实时监控窗口...
echo.
echo  关闭全部服务：关闭弹出的 4 个窗口即可
echo    Backend / Agent / Frontend / Monitor
echo.

REM 启动监控窗口（前台运行，主 bat 退出后仍保留）
if exist "%MONITOR_PS1%" (
    start "GameDie Monitor" powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%MONITOR_PS1%"
)

REM 主窗口立即退出，避免多一个 cmd 窗口
exit
