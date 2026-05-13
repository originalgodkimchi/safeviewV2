# backend/routers/roi.py — ROI 관리 라우터

import sys
import os
import base64
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import cv2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.roi_manager import save_roi, load_roi, list_saved_rois, _roi_path
from core.video_source import VideoSource
from config import DATA_DIR, ROI_DIR

router = APIRouter(prefix="/roi", tags=["roi"])


class PointsBody(BaseModel):
    points: list[list[float]]


class FrameRequest(BaseModel):
    source_path: str


@router.get("")
async def list_rois():
    """저장된 ROI 목록 반환"""
    names = list_saved_rois()
    return {"rois": names}


# 영상 파일 목록은 별도 엔드포인트
@router.get("/videos/list")
async def list_videos():
    """data/ 폴더의 영상 파일 목록"""
    exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    if not os.path.exists(DATA_DIR):
        return {"videos": []}
    files = [
        f for f in os.listdir(DATA_DIR)
        if os.path.splitext(f)[1].lower() in exts
    ]
    return {"videos": sorted(files)}


@router.post("/frame/capture")
async def get_first_frame(body: FrameRequest):
    """소스 첫 프레임을 base64 JPEG으로 반환"""
    source_path = body.source_path
    if not source_path.lower().startswith("rtsp://") and not os.path.isabs(source_path):
        source_path = os.path.join(DATA_DIR, source_path)

    vs = VideoSource(source_path)
    frame = vs.get_first_frame()
    if frame is None:
        raise HTTPException(status_code=400, detail="프레임을 가져올 수 없습니다")

    _, buf = cv2.imencode(".jpg", frame)
    img_b64 = base64.b64encode(buf).decode()
    h, w = frame.shape[:2]
    return {"image": img_b64, "width": w, "height": h}


@router.get("/{name}")
async def get_roi(name: str):
    """특정 ROI 좌표 반환"""
    pts = load_roi(name)
    if pts is None:
        raise HTTPException(status_code=404, detail=f"ROI '{name}' 없음")
    return {"name": name, "points": pts.tolist()}


@router.post("/{name}")
async def save_roi_endpoint(name: str, body: PointsBody):
    """ROI 저장"""
    if len(body.points) < 3:
        raise HTTPException(status_code=400, detail="최소 3개의 꼭짓점이 필요합니다")
    try:
        path = save_roi(name, body.points)
        return {"status": "saved", "path": path, "points": body.points}
    except Exception as e:
        print(f"[ROI] 저장 오류 name={name!r}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
