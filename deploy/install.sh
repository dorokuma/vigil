#!/usr/bin/env bash
set -euo pipefail

echo "=== Server Monitor 部署脚本 ==="

# 1. 检查环境
echo "[1/5] 检查环境..."
command -v python3 >/dev/null 2>&1 || { echo "需要安装 Python 3"; exit 1; }
echo "OK"

# 2. 安装 Python 依赖
echo "[2/5] 安装 Python 依赖..."
cd /root/server-monitor/vigil
pip install -q -r requirements.txt

cd /root/server-monitor/bot
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
deactivate
echo "OK"

# 3. 创建 secrets 文件
echo "[3/5] 创建 secrets 文件..."
if [ ! -f /root/secrets/server-bot.env ]; then
    cat > /root/secrets/server-bot.env << ENVEOF
BOT_TOKEN=your_telegram_bot_token
WORKER_URL=https://api.telegram.org
OPENROUTER_API_KEY=your_openrouter_key
MINIMAX_CN_API_KEY=your_minimax_key
MIHOMO_API_TOKEN=your_mihomo_token
ENVEOF
    chmod 600 /root/secrets/server-bot.env
    echo "  /root/secrets/server-bot.env created - please edit with real values"
else
    echo "  /root/secrets/server-bot.env already exists"
fi

# 4. 部署 systemd 服务
echo "[4/5] 部署 systemd 服务..."
cp /root/server-monitor/deploy/vigil-collector.service /etc/systemd/system/
cp /root/server-monitor/deploy/server-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable vigil-collector.service server-bot.service
echo "OK"

# 5. 启动服务
echo "[5/5] 启动服务..."
systemctl restart vigil-collector.service server-bot.service
echo "OK"

echo ""
echo "=== 部署完成 ==="
echo "查看状态: systemctl status vigil-collector.service server-bot.service"
