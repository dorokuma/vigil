#!/usr/bin/env bash
set -euo pipefail

echo "=== Server Monitor 部署脚本 ==="

# 1. 检查环境
echo "[1/5] 检查环境..."
command -v go >/dev/null 2>&1 || { echo "需要安装 Go"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "需要安装 Python 3"; exit 1; }
echo "OK"

# 2. 编译 Go 引擎
echo "[2/5] 编译 Go 引擎..."
cd /root/server-monitor/engine
go build -o /usr/local/bin/server-monitor .
echo "OK"

# 3. 安装 Python 依赖
echo "[3/5] 安装 Python 依赖..."
cd /root/server-monitor/bot
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
deactivate
echo "OK"

# 4. 部署 systemd 服务
echo "[4/5] 部署 systemd 服务..."
cp /root/server-monitor/deploy/server-monitor.service /etc/systemd/system/
cp /root/server-monitor/deploy/server-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable server-monitor
systemctl enable server-bot
echo "OK"

# 5. 配置 BOT_TOKEN
echo "[5/5] 配置 Bot Token..."
if [ ! -f /etc/systemd/system/server-bot.service ]; then
    echo "请编辑 /etc/systemd/system/server-bot.service，设置："
    echo "  Environment=BOT_TOKEN=你的Token"
    echo "  Environment=WORKER_URL=https://你的域名"
    echo "然后执行: systemctl daemon-reload && systemctl start server-monitor server-bot"
fi

echo ""
echo "=== 部署完成 ==="
echo "查看状态："
echo "  systemctl status server-monitor"
echo "  systemctl status server-bot"
echo "查看日志："
echo "  journalctl -u server-monitor -f"
echo "  journalctl -u server-bot -f"
