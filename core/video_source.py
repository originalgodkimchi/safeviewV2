# core/video_source.py — 영상 입력 소스 관리 모듈

import cv2
import os
import time

os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|timeout;5000000",
)


class VideoSource:
    def __init__(self, source: str):
        self.source       = source
        self.cap          = None
        self.is_rtsp      = source.lower().startswith("rtsp://")
        self._frame_count = 0
        self._consec_fail = 0

    def open(self, timeout_sec: float = 5.0) -> bool:
        try:
            if self.is_rtsp:
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                if not os.path.exists(self.source):
                    print(f"[VideoSource] 파일 없음: {self.source}")
                    return False
                self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                print(f"[VideoSource] 열기 실패: {self.source}")
                return False

            self._frame_count = 0
            self._consec_fail = 0
            return True
        except Exception as e:
            print(f"[VideoSource] open() 예외: {e}")
            return False

    def read_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        try:
            ret, frame = self.cap.read()
            if ret:
                self._frame_count += 1
                self._consec_fail = 0
            else:
                self._consec_fail += 1
            return ret, frame
        except Exception as e:
            print(f"[VideoSource] read_frame() 예외: {e}")
            self._consec_fail += 1
            return False, None

    def reconnect(self, max_attempts: int = 3, wait_sec: float = 2.0) -> bool:
        if not self.is_rtsp:
            return False
        self.release()
        for attempt in range(1, max_attempts + 1):
            print(f"[VideoSource] RTSP 재연결 시도 {attempt}/{max_attempts}...")
            time.sleep(wait_sec)
            if self.open():
                return True
        return False

    def get_fps(self) -> float:
        if self.cap and self.cap.isOpened():
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            return fps if fps > 0 else 25.0
        return 25.0

    def get_frame_size(self) -> tuple[int, int]:
        if self.cap and self.cap.isOpened():
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if w > 0 and h > 0:
                return w, h
        return 640, 480

    def get_total_frames(self) -> int:
        if self.cap and not self.is_rtsp:
            return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return -1

    def get_first_frame(self):
        vs = VideoSource(self.source)
        if not vs.open():
            return None
        frame = None
        if vs.is_rtsp:
            # RTSP: 버퍼 안정화 대기 후 여러 프레임 읽어 마지막 유효 프레임 반환
            time.sleep(1.5)
            for _ in range(15):
                ret, f = vs.cap.read()
                if ret and f is not None:
                    frame = f
        else:
            ret, f = vs.cap.read()
            if ret and f is not None:
                frame = f
        vs.release()
        return frame

    def reset(self):
        if self.cap and not self.is_rtsp:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._frame_count = 0

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self._frame_count = 0
        self._consec_fail = 0

    def is_open(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def consecutive_failures(self) -> int:
        return self._consec_fail


def validate_rtsp_url(url: str) -> tuple[bool, str]:
    if not url.strip():
        return False, "RTSP 주소를 입력하세요."
    if not url.lower().startswith("rtsp://"):
        return False, "주소는 rtsp:// 로 시작해야 합니다."
    if "[" in url or "]" in url:
        return False, "예시 주소의 [ID], [PW], [IP] 부분을 실제 값으로 교체하세요."
    body = url[7:]
    if "@" not in body:
        return False, "주소에 계정 정보(ID:PW@IP)가 필요합니다."
    return True, ""


def test_rtsp_connection(url: str, timeout_sec: float = 5.0) -> tuple[bool, str]:
    valid, err = validate_rtsp_url(url)
    if not valid:
        return False, err
    vs = VideoSource(url)
    if not vs.open():
        return False, "연결 실패: IP/포트/경로 또는 방화벽을 확인하세요."
    ret, frame = vs.cap.read()
    vs.release()
    if ret and frame is not None:
        h, w = frame.shape[:2]
        return True, f"연결 성공! 해상도: {w}×{h}"
    else:
        return False, "연결은 됐지만 프레임을 받지 못했습니다. 채널 경로를 확인하세요."
