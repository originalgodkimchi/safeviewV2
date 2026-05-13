# backend/main.py — FastAPI 앱 진입점

import sys
import os
import asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from backend.session import session
from backend.routers import monitoring, roi, events
from core.event_saver import get_recent_events
from config import EVENTS_DIR, DATA_DIR

app = FastAPI(title="SAFEVIEW API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(monitoring.router, prefix="/api")
app.include_router(roi.router, prefix="/api")
app.include_router(events.router, prefix="/api")

# saved_events 정적 파일 서빙
os.makedirs(EVENTS_DIR, exist_ok=True)
app.mount("/events-files", StaticFiles(directory=EVENTS_DIR), name="events-files")


# ------------------------------------------------------------------
# MJPEG 스트리밍
# ------------------------------------------------------------------

async def generate_frames():
    while True:
        frame_bytes = session.get_latest_frame_bytes()
        if frame_bytes:
            yield (
                b"--boundary\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )
        await asyncio.sleep(0.2 if session.remote_mode else 0.033)


@app.get("/api/stream")
async def stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace;boundary=boundary",
    )


# ------------------------------------------------------------------
# WebSocket 상태 전송
# ------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            status = session.get_status()
            status["recent_events"] = get_recent_events(4)
            await websocket.send_json(status)
            await asyncio.sleep(0.2)
    except Exception:
        pass


@app.get("/api/videos")
async def list_videos():
    """data/ 폴더의 영상 파일 목록 (루트 레벨 편의 엔드포인트)"""
    exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    if not os.path.exists(DATA_DIR):
        return {"videos": []}
    files = sorted(
        f for f in os.listdir(DATA_DIR)
        if os.path.splitext(f)[1].lower() in exts
    )
    return {"videos": files}


@app.post("/api/videos/upload")
async def upload_video(file: UploadFile = File(...)):
    """data/ 폴더에 영상 파일 업로드"""
    exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in exts:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다")
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, file.filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"filename": file.filename, "size": len(content)}


@app.get("/")
async def root():
    return {"message": "SAFEVIEW API is running", "docs": "/docs"}
