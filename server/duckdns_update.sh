#!/bin/bash
# DuckDNS IP 자동 갱신 스크립트
# 설치: crontab -e → */5 * * * * /home/ubuntu/safeviewV2/server/duckdns_update.sh

DOMAIN="your-name"          # DuckDNS 서브도메인 (앞부분만)
TOKEN="your-duckdns-token"  # DuckDNS 토큰

curl -sk "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=" -o /tmp/duckdns.log
