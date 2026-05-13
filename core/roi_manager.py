# core/roi_manager.py — ROI 저장·불러오기·판단 모듈

import os
import json
import numpy as np
import cv2
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ROI_DIR, COLOR_ROI


def _roi_path(source_name: str) -> str:
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in source_name)
    return os.path.join(ROI_DIR, f"{safe_name}.json")


def save_roi(source_name: str, points: list) -> str:
    os.makedirs(ROI_DIR, exist_ok=True)
    path = _roi_path(source_name)
    data = {
        "source": source_name,
        "points": [[int(p[0]), int(p[1])] for p in points],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_roi(source_name: str):
    path = _roi_path(source_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pts = np.array(data["points"], dtype=np.int32)
        if len(pts) < 3:
            return None
        return pts
    except Exception as e:
        print(f"[ROI] 불러오기 실패: {e}")
        return None


def list_saved_rois() -> list[str]:
    if not os.path.exists(ROI_DIR):
        return []
    names = []
    for fname in os.listdir(ROI_DIR):
        if fname.endswith(".json"):
            path = os.path.join(ROI_DIR, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                names.append(data.get("source", fname.replace(".json", "")))
            except Exception:
                names.append(fname.replace(".json", ""))
    return names


def is_point_in_roi(point: tuple, roi_polygon) -> bool:
    if roi_polygon is None or len(roi_polygon) < 3:
        return False
    result = cv2.pointPolygonTest(
        roi_polygon.reshape((-1, 1, 2)).astype(np.int32),
        (float(point[0]), float(point[1])),
        False,
    )
    return result >= 0


def draw_roi_on_frame(frame, roi_polygon, danger: bool = False):
    if roi_polygon is None or len(roi_polygon) < 3:
        return frame
    pts = roi_polygon.reshape((-1, 1, 2)).astype(np.int32)
    color = (0, 0, 200) if danger else COLOR_ROI
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], color)
    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
    for i, pt in enumerate(roi_polygon):
        cv2.circle(frame, (int(pt[0]), int(pt[1])), 5, color, -1)
    return frame


def parse_roi_text(text: str):
    try:
        points = []
        for token in text.replace("\n", ";").split(";"):
            token = token.strip()
            if not token:
                continue
            parts = token.split(",")
            if len(parts) != 2:
                return None
            x, y = int(parts[0].strip()), int(parts[1].strip())
            points.append([x, y])
        if len(points) < 3:
            return None
        return np.array(points, dtype=np.int32)
    except Exception:
        return None
