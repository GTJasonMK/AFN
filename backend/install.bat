@echo off
chcp 65001 >nul
echo ================================================
echo  Arboris-Novel PyQt Backend 安装脚本
echo ================================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 创建虚拟环境...
python -m venv .venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

echo [2/4] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo [3/4] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

echo [4/4] 创建配置文件...
if not exist .env (
    copy .env.example .env
    echo [完成] 已创建 .env 文件
    echo [提示] 请编辑 .env 文件配置必要参数
) else (
    echo [跳过] .env 文件已存在
)

if not exist storage mkdir storage

echo.
echo ================================================
echo  安装完成！
echo ================================================
echo.
echo 下一步:
echo 1. 编辑 .env 文件配置 API Key
echo 2. 运行 start.bat 启动服务
echo.
pause
