# core/plate_detector.py — 번호판 감지기
#
# 동작 모드:
#   1. license_plate_detector.pt 파일이 루트에 있으면 → YOLO 모델로 정밀 감지
#   2. 없으면 → 차량 bbox 하단 추정 영역으로 fallback
#
# 모델 다운로드 (선택):
#   from ultralytics import YOLO
#   YOLO("keremberke/yolov8n-license-plate-detection")  # HuggingFace Hub

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "license_plate_detector.pt")


class PlateDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO

            if not os.path.exists(MODEL_PATH):
                print("[PlateDetector] 번호판 모델 다운로드 중...")
                tmp = YOLO("keremberke/yolov8n-license-plate-detection")
                tmp.save(MODEL_PATH)
                print(f"[PlateDetector] 모델 저장 완료 → {MODEL_PATH}")

            self.model = YOLO(MODEL_PATH)
            print("[PlateDetector] 번호판 모델 로드됨")

        except Exception as e:
            print(f"[PlateDetector] 모델 로드 실패, 추정 모드로 동작: {e}")

    def detect(self, frame, car_detections: list, conf: float = 0.4) -> list[tuple]:
        """
        번호판 bbox 리스트 반환: [(x1, y1, x2, y2), ...]

        Parameters
        ----------
        frame          : 원본 프레임 (BGR)
        car_detections : danger_result 의 all_cars 리스트
        conf           : 감지 신뢰도 (모델 모드에서만 사용)
        """
        if self.model is not None:
            return self._detect_with_model(frame, conf)
        return self._estimate_from_cars(car_detections)

    def _detect_with_model(self, frame, conf: float) -> list[tuple]:
        try:
            results = self.model(frame, verbose=False, conf=conf)[0]
            plates = []
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plates.append((x1, y1, x2, y2))
            return plates
        except Exception as e:
            print(f"[PlateDetector] 추론 오류: {e}")
            return []

    def _estimate_from_cars(self, car_detections: list) -> list[tuple]:
        """
        차량 bbox 기준 번호판 추정 영역 반환.
        - 세로: 하단 28%
        - 가로: 좌우 12% 안쪽 (범퍼 제외)
        """
        plates = []
        for car in car_detections:
            x1, y1, x2, y2 = car["bbox"]
            w = x2 - x1
            h = y2 - y1
            if w <= 0 or h <= 0:
                continue
            px1 = x1 + int(w * 0.12)
            py1 = y2 - int(h * 0.28)
            px2 = x2 - int(w * 0.12)
            py2 = y2
            plates.append((px1, py1, px2, py2))
        return plates
