# core/danger_logic.py — 위험 상태 판단 로직

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.roi_manager import is_point_in_roi


VEHICLE_CLASSES = {"car", "MOTOR", "truck"}

def check_danger(detections: list, roi_polygon) -> dict:
    persons  = [d for d in detections if d["class_name"] == "person"]
    cars     = [d for d in detections if d["class_name"] in VEHICLE_CLASSES]

    result = {
        "is_danger":         False,
        "has_person":        len(persons) > 0,
        "has_car":           len(cars) > 0,
        "dangerous_persons": [],
        "all_persons":       persons,
        "all_cars":          cars,
    }

    if not persons or not cars:
        return result
    if roi_polygon is None:
        return result

    dangerous = []
    for person in persons:
        if is_point_in_roi(person["bottom_center"], roi_polygon):
            dangerous.append(person)

    if dangerous:
        result["is_danger"] = True
        result["dangerous_persons"] = dangerous

    return result


def draw_detections(frame, danger_result: dict, roi_polygon=None):
    import cv2
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import COLOR_NORMAL, COLOR_DANGER
    from core.roi_manager import draw_roi_on_frame

    is_danger = danger_result["is_danger"]
    frame = draw_roi_on_frame(frame, roi_polygon, danger=is_danger)

    all_detections = danger_result["all_persons"] + danger_result["all_cars"]
    for det in all_detections:
        x1, y1, x2, y2 = det["bbox"]
        color = COLOR_DANGER if is_danger else COLOR_NORMAL
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{det['class_name']} {det['confidence']:.2f}"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - lh - 6), (x1 + lw, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    if is_danger:
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), COLOR_DANGER, 8)

    return frame
