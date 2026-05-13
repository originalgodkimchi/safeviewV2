# core/detector.py — YOLOv8 객체 인식 모듈

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, CLASS_IDS, TARGET_CLASS_IDS

class Detector:
    def __init__(self, model_name: str = YOLO_MODEL):
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_name)
            self.loaded = True
        except Exception as e:
            self.loaded = False
            self.load_error = str(e)
            print(f"[Detector] 모델 로드 실패: {e}")

    def detect(self, frame, conf: float = CONFIDENCE_THRESHOLD) -> list[dict]:
        if not self.loaded:
            return []
        try:
            results = self.model(frame, verbose=False)[0]
        except Exception as e:
            print(f"[Detector] 추론 오류: {e}")
            return []

        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in TARGET_CLASS_IDS:
                continue
            confidence = float(box.conf[0])
            if confidence < conf:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            detections.append({
                "class_id":      cls_id,
                "class_name":    CLASS_IDS.get(cls_id, "unknown"),
                "confidence":    round(confidence, 2),
                "bbox":          (x1, y1, x2, y2),
                "center":        (cx, cy),
                "bottom_center": (cx, y2),
            })
        return detections
