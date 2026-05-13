# backend/routers/monitoring.py — 모니터링 제어 라우터

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import APIRouter
from pydantic import BaseModel

from backend.session import session
from config import DATA_DIR

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class StartRequest(BaseModel):
    source_type: str = "file"   # "file" | "rtsp"
    source_path: str
    source_name: str = ""
    conf: float = 0.4


@router.post("/start")
async def start_monitoring(body: StartRequest):
    """모니터링 세션 시작"""
    is_rtsp = body.source_type == "rtsp"

    source_name = body.source_name
    if not source_name:
        source_name = os.path.basename(body.source_path) if not is_rtsp else body.source_path

    # 파일 소스인 경우 절대경로 확인
    source_path = body.source_path
    if not is_rtsp and not os.path.isabs(source_path):
        source_path = os.path.join(DATA_DIR, source_path)

    session.start(
        source_path=source_path,
        source_name=source_name,
        conf=body.conf,
        is_rtsp=is_rtsp,
    )
    return {"status": "started", "source_name": source_name}


@router.post("/stop")
async def stop_monitoring():
    """모니터링 세션 중지"""
    session.stop()
    return {"status": "stopped"}


@router.get("/status")
async def get_status():
    """현재 세션 상태 조회"""
    return session.get_status()


@router.post("/remote-mode")
async def set_remote_mode(enabled: bool):
    """원격 모드 토글 (해상도 640px, 5FPS)"""
    session.set_remote_mode(enabled)
    return {"remote_mode": enabled}
