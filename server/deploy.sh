#!/bin/bash
# git push 후 서버에서 실행하는 재배포 스크립트
# 실행: bash server/deploy.sh
set -e

APP_DIR="/home/ubuntu/safeviewV2"

echo "[deploy] 코드 업데이트..."
cd "$APP_DIR"
git pull origin main

echo "[deploy] Python 패키지 동기화..."
source venv/bin/activate
pip install -r requirements.txt -q

echo "[deploy] React 빌드..."
cd frontend
npm install --silent
npm run build

echo "[deploy] FastAPI 재시작..."
sudo systemctl restart safeview-v2

echo "[deploy] 완료 ✓ → https://$(grep server_name /etc/nginx/sites-available/safeview-v2 | head -1 | awk '{print $2}' | tr -d ';')"
