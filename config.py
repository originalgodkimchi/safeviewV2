# config.py — 전역 설정값 모음

import os

YOLO_MODEL = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.4

CLASS_IDS = {
    0: "person",
    2: "car",
    3: "MOTOR",
    7: "truck",
}
TARGET_CLASS_IDS = [0, 2, 3, 7]

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(BASE_DIR, "data")
EVENTS_DIR      = os.path.join(BASE_DIR, "saved_events")
ROI_DIR         = os.path.join(BASE_DIR, "roi_configs")
LOGS_DIR        = os.path.join(BASE_DIR, "logs")
LOG_FILE        = os.path.join(LOGS_DIR, "events_log.csv")

FRAME_SKIP      = 2
CLIP_PRE_SEC    = 5
CLIP_POST_SEC   = 5
MAX_CLIP_FPS    = 10

COLOR_ROI        = (0, 255, 255)
COLOR_NORMAL     = (0, 200, 0)
COLOR_DANGER     = (0, 0, 220)
COLOR_WARNING_BG = (0, 0, 180)

PRESET_SOURCES = {
    "샘플 영상 (data 폴더에서 선택)": "__file__",
    "자택 CCTV (RTSP 직접 입력)":    "__rtsp__",
}
