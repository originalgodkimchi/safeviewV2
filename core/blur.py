# core/blur.py — 개인정보 보호 블러 처리
#
# 적용 대상:
#   - 사람(person) 전체 bbox
#   - 차량 번호판 bbox
#
# 처리 순서 (session.py 에서):
#   1. YOLO 감지 (원본 프레임 사용)
#   2. vis_frame = frame.copy()
#   3. apply_privacy_blur(vis_frame, ...)   ← 블러 먼저
#   4. draw_detections(vis_frame, ...)      ← 박스는 블러 위에

import cv2


def _gaussian_blur(frame, x1: int, y1: int, x2: int, y2: int, ksize: int):
    """지정 영역에 가우시안 블러 적용 (in-place)"""
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return
    k = ksize if ksize % 2 == 1 else ksize + 1   # 커널은 홀수여야 함
    roi = frame[y1:y2, x1:x2]
    frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)


def apply_privacy_blur(
    frame,
    persons: list,
    plate_bboxes: list[tuple],
    person_blur: int = 31,
    plate_blur: int = 41,
):
    """
    사람과 번호판에 약블러 적용.

    Parameters
    ----------
    frame        : 시각화 프레임 (BGR, in-place 수정)
    persons      : danger_result["all_persons"] 리스트
    plate_bboxes : PlateDetector.detect() 반환값
    person_blur  : 사람 블러 강도 (커널 크기, 홀수)
    plate_blur   : 번호판 블러 강도
    """
    # 사람 전체 영역 블러
    for p in persons:
        x1, y1, x2, y2 = p["bbox"]
        _gaussian_blur(frame, x1, y1, x2, y2, ksize=person_blur)

    # 번호판 영역 블러
    for (x1, y1, x2, y2) in plate_bboxes:
        _gaussian_blur(frame, x1, y1, x2, y2, ksize=plate_blur)
