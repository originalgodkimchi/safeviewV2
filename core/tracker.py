# core/tracker.py — 빠른 객체를 위한 간단한 다중 객체 추적기
#
# 동작 원리:
#   - YOLO 감지 결과를 받아 기존 트랙과 매칭
#   - IoU가 낮아도 중심점 거리로 보완 매칭 (빠른 오토바이 대응)
#   - 매칭 실패해도 max_age 프레임 동안 마지막 위치 유지
#   - max_age 초과 시 트랙 제거

def _iou(b1, b2):
    ix1 = max(b1[0], b2[0])
    iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2])
    iy2 = min(b1[3], b2[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def _match_score(t_det, n_det):
    """두 감지 결과의 유사도 (0 = 매칭 불가, 1 = 완전 일치)"""
    if t_det["class_id"] != n_det["class_id"]:
        return 0.0

    # 1차: IoU
    score = _iou(t_det["bbox"], n_det["bbox"])
    if score >= 0.15:
        return score

    # 2차: 중심점 거리 (빠른 객체 보완)
    cx1, cy1 = t_det["center"]
    cx2, cy2 = n_det["center"]
    dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5

    bx1, by1, bx2, by2 = t_det["bbox"]
    obj_size = ((bx2 - bx1) + (by2 - by1)) / 2
    if obj_size <= 0:
        return 0.0

    # 객체 크기의 4배 이내면 같은 객체로 간주
    if dist < obj_size * 4:
        return 0.3 * (1.0 - dist / (obj_size * 4))

    return 0.0


class DetectionTracker:
    """
    간단한 IoU + 거리 기반 다중 객체 추적기.

    Parameters
    ----------
    max_age : int
        YOLO에서 감지 안 돼도 트랙을 유지할 최대 프레임 수.
        빠른 오토바이는 값을 크게 (8~12) 설정하면 깜빡임이 줄어듦.
    min_score : float
        매칭으로 인정하는 최소 유사도.
    """

    def __init__(self, max_age: int = 10, min_score: float = 0.15):
        self.max_age   = max_age
        self.min_score = min_score
        self._tracks: list[dict] = []  # {det, age}
        self._next_track_id = 1

    def update(self, detections: list[dict]) -> list[dict]:
        """
        새 YOLO 감지 결과로 트랙을 갱신하고 현재 살아있는 전체 트랙 반환.

        Parameters
        ----------
        detections : YOLO에서 나온 감지 결과 리스트 (빈 리스트도 OK)

        Returns
        -------
        살아있는 트랙의 감지 결과 리스트 (기존 + 새로운)
        """
        # 모든 트랙 노화
        for t in self._tracks:
            t["age"] += 1

        matched_track_idx = set()
        matched_det_idx   = set()

        # 새 감지 → 기존 트랙 매칭 (탐욕적 best-match)
        for di, det in enumerate(detections):
            best_score = self.min_score
            best_ti    = -1
            for ti, track in enumerate(self._tracks):
                if ti in matched_track_idx:
                    continue
                score = _match_score(track["det"], det)
                if score > best_score:
                    best_score = score
                    best_ti    = ti

            if best_ti >= 0:
                track_id = self._tracks[best_ti]["track_id"]
                det["track_id"] = track_id
                self._tracks[best_ti]["det"] = det
                self._tracks[best_ti]["age"] = 0
                matched_track_idx.add(best_ti)
                matched_det_idx.add(di)

        # 매칭 안 된 새 감지 → 신규 트랙 생성
        for di, det in enumerate(detections):
            if di not in matched_det_idx:
                track_id = self._next_track_id
                self._next_track_id += 1
                det["track_id"] = track_id
                self._tracks.append({"det": det, "age": 0, "track_id": track_id})

        # 수명 초과 트랙 제거
        self._tracks = [t for t in self._tracks if t["age"] <= self.max_age]

        return [t["det"] for t in self._tracks]

    def reset(self):
        self._tracks.clear()
