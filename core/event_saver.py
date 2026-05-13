# core/event_saver.py — 이벤트 저장 모듈

import cv2
import os
import csv
import subprocess
from datetime import datetime
from collections import deque
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EVENTS_DIR, LOGS_DIR, LOG_FILE, MAX_CLIP_FPS


def _write_h264_via_pipe(frames: list, w: int, h: int, fps: float, filepath: str) -> bool:
    """프레임을 ffmpeg 파이프로 직접 전달해 H.264 mp4 생성 (브라우저 재생 보장)"""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg, "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{w}x{h}", "-pix_fmt", "bgr24", "-r", str(fps),
            "-i", "pipe:0",
            "-vcodec", "libx264", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            filepath,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        for frame in frames:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        proc.wait(timeout=120)
        return proc.returncode == 0 and os.path.exists(filepath)
    except Exception as e:
        print(f"[EventSaver] ffmpeg 파이프 실패: {e}")
        return False


def ensure_dirs():
    os.makedirs(EVENTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def save_event_image(frame, source_name: str) -> tuple[str, str]:
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in source_name)
    filename = f"event_{safe_name}_{timestamp}.jpg"
    filepath = os.path.join(EVENTS_DIR, filename)
    cv2.imwrite(filepath, frame)
    return filename, filepath


def save_event_clip(frame_buffer: deque, source_name: str, fps: float = MAX_CLIP_FPS) -> tuple[str | None, str | None]:
    ensure_dirs()
    if not frame_buffer:
        return None, None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in source_name)
    filename = f"clip_{safe_name}_{timestamp}.mp4"
    filepath = os.path.join(EVENTS_DIR, filename)

    frames = list(frame_buffer)
    h, w = frames[0].shape[:2]

    if not _write_h264_via_pipe(frames, w, h, float(fps), filepath):
        # ffmpeg 실패 시 mp4v fallback
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(filepath, fourcc, float(fps), (w, h))
        for f in frames:
            writer.write(f)
        writer.release()

    return filename, filepath


def log_event(source_name: str, image_filename: str, clip_filename: str = None):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "source", "status", "image_file", "clip_file"])
        writer.writerow([timestamp, source_name, "위험", image_filename, clip_filename or ""])


def get_recent_events(n: int = 10) -> list[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return rows[-n:][::-1]
    except Exception as e:
        print(f"[EventSaver] 로그 읽기 오류: {e}")
        return []


def get_event_image_path(filename: str) -> str | None:
    path = os.path.join(EVENTS_DIR, filename)
    return path if os.path.exists(path) else None
