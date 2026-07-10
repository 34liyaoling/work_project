#!/bin/bash

echo "========================================"
echo "  招聘数据采集工具"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.8+"
    exit 1
fi

# 检查requests是否安装
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 正在安装依赖..."
    pip3 install requests -q
fi

echo "[提示] 开始采集数据..."
echo

# 运行采集
python3 collector.py "$@"

echo
echo "========================================"
echo "  采集完成！"
echo "========================================"
