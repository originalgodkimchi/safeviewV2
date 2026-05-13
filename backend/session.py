# backend/session.py — 모니터링 세션 싱글턴

import sys
import os
import threading
import time
import cv2
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import FRAME_SKIP, CLIP_PRE_SEC, CLIP_POST_SEC, MAX_CLIP_FPS
from core.detector import Detector
from core.roi_manager import load_roi, draw_roi_on_frame
from core.roi_manager import is_point_in_roi
from core.video_source import VideoSource
from core.danger_logic import check_danger, draw_detections
from core.event_saver import save_event_image, save_event_clip, log_event
from core.tracker import DetectionTracker


class MonitoringSession:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._frame_lock = threading.Lock()
        self._latest_frame_bytes: bytes | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._remote_mode = False

        self._status = {
            "running": False,
            "is_danger": False,
            "fps": 0.0,
            "frame_idx": 0,
            "persons": 0,
            "cars": 0,
            "roi_loaded": False,
            "source_name": "",
            "error": "",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, source_path: str, source_name: str, conf: float = 0.4, is_rtsp: bool = False):
        if self._status["running"]:
            self.stop()

        self._stop_event.clear()
        self._status.update({
            "running": True,
            "is_danger": False,
            "fps": 0.0,
            "frame_idx": 0,
            "persons": 0,
            "cars": 0,
            "roi_loaded": False,
            "source_name": source_name,
            "error": "",
        })

        # 스레드 시작 전 플레이스홀더 프레임 설정
        # → 브라우저가 첫 프레임을 받을 때까지 회색으로 멈추지 않도록
        self._set_placeholder_frame()

        self._thread = threading.Thread(
            target=self._run,
            args=(source_path, source_name, conf, is_rtsp),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._status["running"] = False
        with self._frame_lock:
            self._latest_frame_bytes = None

    def get_latest_frame_bytes(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_frame_bytes

    def get_status(self) -> dict:
        return dict(self._status)

    def set_remote_mode(self, enabled: bool):
        self._remote_mode = enabled

    @property
    def remote_mode(self) -> bool:
        return self._remote_mode

    # ------------------------------------------------------------------
    # Internal processing loop
    # ------------------------------------------------------------------

    def _run(self, source_path: str, source_name: str, conf: float, is_rtsp: bool):
        detector = Detector()
        if not detector.loaded:
            self._status["error"] = f"모델 로드 실패: {detector.load_error}"
            self._status["running"] = False
            return

        roi_polygon = load_roi(source_name)
        self._status["roi_loaded"] = roi_polygon is not None

        vs = VideoSource(source_path)
        opened = False
        attempts = 3 if is_rtsp else 1
        for attempt in range(1, attempts + 1):
            if vs.open():
                opened = True
                break
            if is_rtsp:
                print(f"[Session] RTSP 연결 시도 {attempt}/{attempts} 실패, 재시도 중...")
                time.sleep(2)
        if not opened:
            self._status["error"] = "영상 소스를 열 수 없습니다. URL·파일 경로를 확인하세요."
            self._status["running"] = False
            return

        source_fps = vs.get_fps()
        pre_buf_size = max(1, int(source_fps * CLIP_PRE_SEC))
        post_buf_size = max(1, int(source_fps * CLIP_POST_SEC))
        frame_buffer: deque = deque(maxlen=pre_buf_size + post_buf_size)

        tracker = DetectionTracker(max_age=10, min_score=0.15)

        frame_idx = 0
        fps_counter = 0
        fps_timer = time.time()
        in_event = False
        post_frames_remaining = 0
        consec_fail = 0
        person_roi_state: dict[int, bool] = {}
        danger_latch_frames = 0

        last_danger_result = {
            "is_danger": False, "has_person": False, "has_car": False,
            "dangerous_persons": [], "all_persons": [], "all_cars": [],
        }

        while not self._stop_event.is_set():
            ret, frame = vs.read_frame()

            if not ret:
                consec_fail += 1
                if is_rtsp:
                    # 30프레임 연속 실패 시에만 재연결 시도 (일시적 패킷 손실 무시)
                    if consec_fail >= 30:
                        print(f"[Session] RTSP 연속 실패 {consec_fail}회, 재연결 시도...")
                        if vs.reconnect():
                            consec_fail = 0
                        else:
                            self._status["error"] = "RTSP 재연결 실패. 스트림을 확인하세요."
                            break
                    time.sleep(0.03)
                else:
                    vs.reset()
                    consec_fail = 0
                continue

            consec_fail = 0
            frame_idx += 1
            fps_counter += 1

            # FPS 계산
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                self._status["fps"] = round(fps_counter / elapsed, 1)
                fps_counter = 0
                fps_timer = time.time()

            # YOLO 감지 (FRAME_SKIP마다 실행, 나머지는 트래커 결과 재사용)
            try:
                if frame_idx % (FRAME_SKIP + 1) == 0 or frame_idx == 1:
                    raw_detections = detector.detect(frame, conf=conf)
                    tracked = tracker.update(raw_detections)
                else:
                    tracked = tracker.update([])
                danger_result = check_danger(tracked, roi_polygon)
                last_danger_result = danger_result
            except Exception as e:
                print(f"[Session] 감지 오류: {e}")
                danger_result = last_danger_result

            # person이 ROI 내부 -> 외부로 이동한 프레임을 위험 이벤트로 간주
            person_exit_detected = False
            if roi_polygon is not None:
                visible_person_ids = set()
                for person in danger_result["all_persons"]:
                    track_id = person.get("track_id")
                    if track_id is None:
                        continue
                    visible_person_ids.add(track_id)
                    inside_now = is_point_in_roi(person["bottom_center"], roi_polygon)
                    inside_prev = person_roi_state.get(track_id)
                    if inside_prev is True and not inside_now:
                        person_exit_detected = True
                    person_roi_state[track_id] = inside_now

                for track_id in list(person_roi_state.keys()):
                    if track_id not in visible_person_ids:
                        del person_roi_state[track_id]

            if person_exit_detected:
                # UI에서 사람이 빠르게 지나가도 '위험' 배지가 보이도록 잠시 유지
                danger_latch_frames = max(1, int(source_fps * 1.5))
            elif danger_latch_frames > 0:
                danger_latch_frames -= 1

            is_danger_now = (
                danger_result["is_danger"]
                or person_exit_detected
                or danger_latch_frames > 0
            )
            danger_result["is_danger"] = is_danger_now

            self._status.update({
                "frame_idx": frame_idx,
                "persons": len(danger_result["all_persons"]),
                "cars": len(danger_result["all_cars"]),
                "is_danger": is_danger_now,
            })

            # 시각화
            vis_frame = frame.copy()

            try:
                vis_frame = draw_detections(vis_frame, danger_result, roi_polygon)
            except Exception as e:
                print(f"[Session] 시각화 오류: {e}")

            self._encode_frame(vis_frame, None, None)

            # 프레임 버퍼 업데이트
            frame_buffer.append(frame.copy())

            # 이벤트 저장
            is_danger = is_danger_now
            if is_danger and not in_event:
                in_event = True
                post_frames_remaining = post_buf_size
            elif in_event:
                if post_frames_remaining > 0:
                    post_frames_remaining -= 1
                if post_frames_remaining == 0:
                    in_event = False
                    try:
                        img_name, _ = save_event_image(vis_frame, source_name)
                        clip_frames = deque(list(frame_buffer), maxlen=len(frame_buffer))
                        clip_name, _ = save_event_clip(clip_frames, source_name, fps=min(source_fps, MAX_CLIP_FPS))
                        log_event(source_name, img_name, clip_name)
                    except Exception as e:
                        print(f"[Session] 이벤트 저장 오류: {e}")

        vs.release()
        self._status["running"] = False

    def _set_placeholder_frame(self, width: int = 640, height: int = 360):
        """회색 플레이스홀더 프레임을 설정해 스트림이 즉시 응답하도록 함"""
        import numpy as np
        placeholder = np.full((height, width, 3), 50, dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 60])
        with self._frame_lock:
            self._latest_frame_bytes = buf.tobytes()

    def _encode_frame(self, frame, roi_polygon, danger_result):
        try:
            if self._remote_mode:
                h, w = frame.shape[:2]
                if w > 640:
                    scale = 640 / w
                    frame = cv2.resize(frame, (640, int(h * scale)))
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            with self._frame_lock:
                self._latest_frame_bytes = buf.tobytes()
        except Exception as e:
            print(f"[Session] 프레임 인코딩 오류: {e}")


# 싱글턴 인스턴스
session = MonitoringSession()
