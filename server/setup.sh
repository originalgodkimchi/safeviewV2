#!/bin/bash
# Oracle Cloud Ubuntu 22.04 ARM A1 초기 설정
# 실행: bash server/setup.sh
set -e

APP_DIR="/home/ubuntu/safeviewV2"
MEDIAMTX_VERSION="v1.9.1"

echo "======================================"
echo " SAFEVIEW 서버 초기 설정"
echo "======================================"

# ── 1. 시스템 패키지 ─────────────────────
echo "[1/7] 시스템 패키지 설치..."
sudo apt update -y && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx \
    certbot python3-certbot-nginx curl wget nodejs npm

# Node.js 최신 LTS 설치 (apt 버전이 오래될 수 있음)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# ── 2. Python 환경 + 패키지 ──────────────
echo "[2/7] Python 환경 설정..."
cd "$APP_DIR"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# ── 3. React 빌드 ────────────────────────
echo "[3/7] React 프론트엔드 빌드..."
cd "$APP_DIR/frontend"
npm install
npm run build
echo "빌드 완료 → frontend/dist/"

# ── 4. MediaMTX 설치 ─────────────────────
echo "[4/7] MediaMTX 설치..."
cd /tmp
wget -q "https://github.com/bluenviron/mediamtx/releases/download/${MEDIAMTX_VERSION}/mediamtx_${MEDIAMTX_VERSION}_linux_arm64v8.tar.gz"
tar xf mediamtx_*.tar.gz
sudo mv mediamtx /usr/local/bin/mediamtx
sudo chmod +x /usr/local/bin/mediamtx
sudo cp "$APP_DIR/server/mediamtx.yml" /etc/mediamtx.yml

# ── 5. 런타임 디렉토리 ───────────────────
echo "[5/7] 런타임 디렉토리 생성..."
mkdir -p "$APP_DIR/data" "$APP_DIR/saved_events" \
         "$APP_DIR/logs" "$APP_DIR/roi_configs"

# ── 6. systemd 서비스 ────────────────────
echo "[6/7] systemd 서비스 등록..."
sudo cp "$APP_DIR/server/safeview-v2.service"  /etc/systemd/system/
sudo cp "$APP_DIR/server/mediamtx.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable safeview-v2 mediamtx

# ── 7. 방화벽 + nginx ────────────────────
echo "[7/7] 방화벽 + nginx 설정..."
sudo apt install -y iptables-persistent
sudo iptables -I INPUT 6 -p tcp --dport 80   -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443  -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 8554 -j ACCEPT
sudo iptables -I INPUT 6 -p udp --dport 8554 -j ACCEPT
sudo netfilter-persistent save

sudo cp "$APP_DIR/server/nginx.conf" /etc/nginx/sites-available/safeview-v2
sudo ln -sf /etc/nginx/sites-available/safeview-v2 /etc/nginx/sites-enabled/safeview-v2
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "======================================"
echo " 설정 완료! 다음 단계:"
echo ""
echo " 1. nginx.conf 도메인 교체"
echo "    sudo sed -i 's/your-name/실제서브도메인/g' /etc/nginx/sites-available/safeview-v2"
echo "    sudo nginx -s reload"
echo ""
echo " 2. HTTPS 인증서 발급"
echo "    sudo certbot --nginx -d 실제도메인.duckdns.org"
echo ""
echo " 3. 서비스 시작"
echo "    sudo systemctl start mediamtx safeview-v2"
echo "======================================"
