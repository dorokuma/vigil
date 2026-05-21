#!/bin/bash
#
# deploy/setup-cloudflare-tunnel.sh
# 一键配置 Cloudflare Tunnel（免费白嫖，无需公网 IP）

set -e

echo "🌐 Vigil Cloudflare Tunnel 一键配置"
echo ""

echo "[1/4] 检查 cloudflared..."
if ! command -v cloudflared &> /dev/null; then
    echo "正在安装 cloudflared..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install cloudflared
    else
        curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
        sudo dpkg -i cloudflared.deb
        rm cloudflared.deb
    fi
fi

echo "[2/4] 登录 Cloudflare..."
cloudflared tunnel login

echo "[3/4] 创建 Tunnel..."
read -p "请输入 Tunnel 名称 (例如: vigil-collector): " TUNNEL_NAME
cloudflared tunnel create $TUNNEL_NAME

TUNNEL_ID=$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}')

echo "[4/4] 配置路由..."
read -p "请输入你的域名 (例如: vigil.yourdomain.com): " DOMAIN

cloudflared tunnel route dns $TUNNEL_NAME $DOMAIN

cat > config.yml << EOF
url: http://127.0.0.1:9901
 tunnel: $TUNNEL_ID
 credentials-file: /root/.cloudflared/$TUNNEL_ID.json
EOF

echo ""
echo "✅ 配置完成！"
echo ""
echo "启动命令："
echo "  cloudflared tunnel --config config.yml run $TUNNEL_NAME"
echo ""
echo "现在你的 Vigil 采集端可以通过 https://$DOMAIN 安全访问了！"
echo "（完全免费，无需公网 IP）"
