# backend/routers/events.py — 이벤트 조회 라우터

import sys
import os
import csv
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import APIRouter, Query
from config import LOG_FILE, EVENTS_DIR, ROI_DIR, DATA_DIR

router = APIRouter(prefix="/events", tags=["events"])


def _read_log() -> list[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"[events] CSV 읽기 오류: {e}")
        return []


@router.get("")
async def get_events(date: str = Query(None, description="YYYY-MM-DD 형식 날짜 필터")):
    """전체 이벤트 목록 (선택적 날짜 필터)"""
    rows = _read_log()
    if date:
        rows = [r for r in rows if r.get("timestamp", "").startswith(date)]
    # 최신 순 정렬
    rows = list(reversed(rows))
    return {"events": rows, "total": len(rows)}


@router.get("/stats")
async def get_stats():
    """이벤트 통계"""
    rows = _read_log()
    total = len(rows)

    # 날짜 수
    dates = set()
    for r in rows:
        ts = r.get("timestamp", "")
        if ts:
            dates.add(ts[:10])

    # 이미지/클립 수
    images = 0
    clips = 0
    storage_bytes = 0
    if os.path.exists(EVENTS_DIR):
        for fname in os.listdir(EVENTS_DIR):
            fpath = os.path.join(EVENTS_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            size = os.path.getsize(fpath)
            storage_bytes += size
            if fname.startswith("event_") and fname.endswith(".jpg"):
                images += 1
            elif fname.startswith("clip_") and fname.endswith(".mp4"):
                clips += 1

    # 샘플 영상 수
    exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    sample_videos = 0
    if os.path.exists(DATA_DIR):
        sample_videos = sum(
            1 for f in os.listdir(DATA_DIR)
            if os.path.splitext(f)[1].lower() in exts
        )

    # 저장된 ROI 수
    roi_count = 0
    if os.path.exists(ROI_DIR):
        roi_count = sum(1 for f in os.listdir(ROI_DIR) if f.endswith(".json"))

    return {
        "total": total,
        "dates_count": len(dates),
        "images": images,
        "clips": clips,
        "storage_mb": round(storage_bytes / 1024 / 1024, 2),
        "sample_videos": sample_videos,
        "roi_count": roi_count,
    }


@router.get("/dates")
async def get_event_dates():
    """이벤트가 있는 날짜 목록"""
    rows = _read_log()
    dates = sorted(
        set(r["timestamp"][:10] for r in rows if r.get("timestamp")),
        reverse=True,
    )
    return {"dates": dates}
