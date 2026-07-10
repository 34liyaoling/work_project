@echo off
chcp 65001 >nul
echo ========================================
echo   招聘数据采集工具
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查requests是否安装
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install requests -q
)

echo [提示] 开始采集数据...
echo.

REM 运行采集
python collector.py %*

echo.
echo ========================================
echo   采集完成！
echo ========================================
pause
