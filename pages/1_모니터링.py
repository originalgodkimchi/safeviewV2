# pages/1_모니터링.py — 실시간 위험 감지

import streamlit as st
import cv2, os, sys, time, threading
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import DATA_DIR, FRAME_SKIP, CLIP_PRE_SEC, CLIP_POST_SEC, MAX_CLIP_FPS
from core.detector     import Detector
from core.roi_manager  import load_roi
from core.video_source import VideoSource, validate_rtsp_url, test_rtsp_connection
from core.danger_logic import check_danger, draw_detections
from core.event_saver  import save_event_image, save_event_clip, log_event, get_recent_events


# ── RTSP 스레드 리더 ────────────────────────────────────
class RTSPThreadReader:
    def __init__(self, url: str):
        self._url          = url
        self._latest_frame = None
        self._lock         = threading.Lock()
        self._stop_event   = threading.Event()
        self._thread       = threading.Thread(target=self._run, daemon=True)
        self._connected    = False
        self._error        = ""
        self._frame_count  = 0

    def start(self) -> tuple[bool, str]:
        self._thread.start()
        for _ in range(60):
            time.sleep(0.1)
            with self._lock:
                if self._latest_frame is not None:
                    return True, ""
            if self._error:
                return False, self._error
        return False, "타임아웃: 6초 내에 첫 프레임을 받지 못했습니다."

    def _run(self):
        vs = VideoSource(self._url)
        if not vs.open():
            self._error = "RTSP 연결 실패"
            return
        self._connected = True
        fail_streak = 0
        while not self._stop_event.is_set():
            ret, frame = vs.cap.read()
            if ret and frame is not None:
                fail_streak = 0
                with self._lock:
                    self._latest_frame = frame
                    self._frame_count += 1
            else:
                fail_streak += 1
                if fail_streak >= 20:
                    vs.release()
                    time.sleep(2.0)
                    if vs.open():
                        fail_streak = 0
                    else:
                        self._error = "재연결 실패"
                        break
                time.sleep(0.05)
        vs.release()

    def get_latest_frame(self):
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def stop(self):
        self._stop_event.set()

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def error(self) -> str:
        return self._error


# ── 페이지 설정 ─────────────────────────────────────────
st.set_page_config(
    page_title="모니터링 | SAFE VIEW",
    page_icon="🎥",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

[data-testid="stAppViewContainer"] { background: #f8fffe; }
[data-testid="stMain"] { background: #f8fffe; }
[data-testid="stSidebar"] { background: #f0fdf4; border-right: 2px solid #bbf7d0; }
[data-testid="stSidebarContent"] { background: #f0fdf4; }
body, p, span, div, label { color: #111827; }
h1, h2, h3, h4 { color: #111827; }

[data-testid="stSidebarNav"] a { color: #374151 !important; border-radius: 8px; padding: 8px 12px; font-weight: 500; }
[data-testid="stSidebarNav"] a:hover { color: #16a34a !important; background: #dcfce7 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { color: #15803d !important; background: #bbf7d0 !important; font-weight: 600; }

hr { border-color: #d1fae5 !important; }

[data-testid="metric-container"] {
    background: #ffffff; border: 1.5px solid #86efac;
    border-radius: 12px; padding: 12px !important;
    box-shadow: 0 1px 4px rgba(22,163,74,0.08);
}
[data-testid="stMetricValue"] { color: #16a34a !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #6b7280 !important; }

.stButton > button {
    background: #ffffff; color: #374151;
    border: 1.5px solid #d1d5db; border-radius: 8px;
    font-weight: 500; transition: all 0.2s;
}
.stButton > button:hover { background: #f0fdf4; border-color: #16a34a; color: #16a34a; }
.stButton > button[kind="primary"] {
    background: #16a34a; border-color: #16a34a;
    color: #ffffff; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { background: #15803d; border-color: #15803d; }

.stSlider [data-baseweb="slider"] { color: #16a34a !important; }
.stSelectbox [data-baseweb="select"] > div {
    background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
}
.stTextInput input {
    background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
}
.stRadio label { color: #374151 !important; }
</style>
""", unsafe_allow_html=True)


# ── 상태 초기화 ─────────────────────────────────────────
def init_state():
    defaults = {
        "running": False, "prev_danger": False, "frame_idx": 0,
        "last_event_ts": 0.0, "fps_timer": time.time(), "fps_count": 0,
        "fps_display": 0.0, "video_source": None, "rtsp_reader": None,
        "detector": None, "frame_buffer": deque(), "source_name": "",
        "is_rtsp": False, "alert_msg": "", "alert_expires": 0.0,
        "last_good_frame": None, "last_detections": [],
        "post_recording": False, "post_rec_start": 0.0,
        "pre_frames": [], "post_frames": [], "pending_img_name": "",
        "rtsp_url_saved": "", "rtsp_cam_name": "rtsp_stream",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def get_video_files() -> list:
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR)
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))]

def update_fps():
    st.session_state.fps_count += 1
    elapsed = time.time() - st.session_state.fps_timer
    if elapsed >= 1.0:
        st.session_state.fps_display = round(st.session_state.fps_count / elapsed, 1)
        st.session_state.fps_count = 0
        st.session_state.fps_timer = time.time()

def stop_all():
    if st.session_state.rtsp_reader:
        st.session_state.rtsp_reader.stop()
        st.session_state.rtsp_reader = None
    if st.session_state.video_source:
        st.session_state.video_source.release()
        st.session_state.video_source = None
    st.session_state.running = False
    st.session_state.last_good_frame = None


# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:18px;font-weight:700;color:#15803d;padding:8px 0 16px;
                display:flex;align-items:center;gap:8px;">
        🎥 <span>모니터링 설정</span>
    </div>
    """, unsafe_allow_html=True)

    source_type = st.radio(
        "영상 소스",
        ["📁 로컬 영상 파일", "📡 RTSP 스트림"],
        disabled=st.session_state.running,
    )

    selected_source = None
    source_label    = ""
    source_ready    = False

    if source_type == "📁 로컬 영상 파일":
        video_files = get_video_files()
        if video_files:
            chosen = st.selectbox("영상 파일", video_files, disabled=st.session_state.running)
            selected_source = os.path.join(DATA_DIR, chosen)
            source_label    = os.path.splitext(chosen)[0]
            source_ready    = True
        else:
            st.warning("`data/` 폴더에 영상 파일을 넣어주세요.")
    else:
        rtsp_url = st.text_input(
            "RTSP 주소",
            value=st.session_state.rtsp_url_saved,
            placeholder="rtsp://admin:1234@192.168.0.100:554/...",
            disabled=st.session_state.running,
        )
        st.session_state.rtsp_url_saved = rtsp_url
        cam_name = st.text_input(
            "카메라 이름",
            value=st.session_state.rtsp_cam_name,
            disabled=st.session_state.running,
        )
        st.session_state.rtsp_cam_name = cam_name

        valid, err = validate_rtsp_url(rtsp_url)
        if rtsp_url and not valid:
            st.error(f"⛔ {err}")
        elif valid:
            st.success("✅ 주소 형식 OK")
            if st.button("연결 테스트", disabled=st.session_state.running):
                with st.spinner("연결 중..."):
                    ok, msg = test_rtsp_connection(rtsp_url)
                (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg}")

        if valid:
            selected_source = rtsp_url
            source_label    = cam_name
            source_ready    = True

    st.markdown("<hr>", unsafe_allow_html=True)

    roi_polygon = load_roi(source_label) if source_label else None
    if roi_polygon is not None:
        st.markdown(f"""
        <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;
                    padding:10px 14px;font-size:13px;">
            <span style="color:#16a34a;font-weight:600;">● ROI 로드됨</span>
            <span style="color:#6b7280;"> — {len(roi_polygon)}개 꼭짓점</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#fffbeb;border:1.5px solid #fcd34d;border-radius:10px;
                    padding:10px 14px;font-size:13px;">
            <span style="color:#d97706;font-weight:600;">⚠ ROI 미설정</span>
            <span style="color:#6b7280;"> — 위험 판단 비활성화</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    conf_threshold = st.slider("탐지 신뢰도", 0.1, 0.9, 0.4, 0.05, disabled=st.session_state.running)

    st.markdown("<hr>", unsafe_allow_html=True)

    remote_mode = st.checkbox(
        "원격 공유 모드 (ngrok)",
        value=st.session_state.get("remote_mode", False),
    )
    st.session_state.remote_mode = remote_mode

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    start_btn = c1.button("▶ 시작", use_container_width=True,
                          disabled=st.session_state.running or not source_ready, type="primary")
    stop_btn  = c2.button("■ 정지", use_container_width=True,
                          disabled=not st.session_state.running)

    if st.session_state.running:
        st.markdown("<br>", unsafe_allow_html=True)
        fa, fb = st.columns(2)
        fa.metric("FPS", st.session_state.fps_display)
        fb.metric("프레임", st.session_state.frame_idx)


# ── 시작/정지 처리 ───────────────────────────────────────
if start_btn and selected_source:
    if st.session_state.detector is None:
        with st.spinner("YOLOv8 모델 로딩 중..."):
            st.session_state.detector = Detector()
        if not st.session_state.detector.loaded:
            st.error(f"모델 로드 실패: {st.session_state.detector.load_error}")
            st.stop()

    is_rtsp = source_type == "📡 RTSP 스트림"
    buf_size = max(int(25 * CLIP_PRE_SEC), 30)

    if is_rtsp:
        valid, err = validate_rtsp_url(selected_source)
        if not valid:
            st.error(f"❌ {err}")
            st.stop()
        with st.spinner("RTSP 연결 중..."):
            reader = RTSPThreadReader(selected_source)
            ok, err_msg = reader.start()
        if not ok:
            st.error(f"RTSP 연결 실패: {err_msg}")
            reader.stop()
            st.stop()
        st.session_state.rtsp_reader  = reader
        st.session_state.video_source = None
    else:
        vs = VideoSource(selected_source)
        with st.spinner("영상 파일 여는 중..."):
            opened = vs.open()
        if not opened:
            st.error("영상 파일을 열 수 없습니다.")
            st.stop()
        st.session_state.video_source = vs
        st.session_state.rtsp_reader  = None

    st.session_state.update({
        "is_rtsp": is_rtsp, "source_name": source_label,
        "frame_idx": 0, "prev_danger": False,
        "frame_buffer": deque(maxlen=buf_size),
        "fps_timer": time.time(), "fps_count": 0, "fps_display": 0.0,
        "running": True, "last_good_frame": None,
        "alert_msg": "", "alert_expires": 0.0,
    })
    st.rerun()

if stop_btn:
    stop_all()
    st.rerun()


# ── 메인 레이아웃 ────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
    <div style="background:#dcfce7;border-radius:10px;padding:8px 10px;font-size:20px;line-height:1;">🎥</div>
    <div style="font-size:20px;font-weight:700;color:#15803d;">실시간 모니터링</div>
</div>
""", unsafe_allow_html=True)

video_col, panel_col = st.columns([3, 1])

with video_col:
    frame_ph = st.empty()
    info_ph  = st.empty()

with panel_col:
    status_ph  = st.empty()
    alert_ph   = st.empty()
    events_ph  = st.empty()


# ── 대기 상태 ────────────────────────────────────────────
if not st.session_state.running:
    frame_ph.markdown("""
    <div style="background:#ffffff;border:2px dashed #86efac;border-radius:14px;
                padding:80px 20px;text-align:center;">
        <div style="font-size:48px;margin-bottom:12px;">📹</div>
        <div style="color:#6b7280;font-size:15px;">왼쪽 패널에서 소스를 선택하고</div>
        <div style="color:#16a34a;font-size:15px;font-weight:600;margin-top:4px;">▶ 시작을 누르세요</div>
    </div>
    """, unsafe_allow_html=True)

    status_ph.markdown("""
    <div style="background:#ffffff;border:1.5px solid #d1d5db;border-radius:12px;
                padding:20px;text-align:center;">
        <div style="font-size:32px;margin-bottom:8px;">⚪</div>
        <div style="font-size:16px;font-weight:600;color:#6b7280;">대기 중</div>
    </div>
    """, unsafe_allow_html=True)

    recent = get_recent_events(5)
    if recent:
        items_html = ""
        for ev in recent:
            items_html += f"""
            <div style="padding:8px 0;border-bottom:1px solid #f0fdf4;font-size:12px;">
                <div style="color:#dc2626;font-weight:600;">● 위험 감지</div>
                <div style="color:#6b7280;">{ev.get('timestamp','')[:19]}</div>
                <div style="color:#6b7280;">{ev.get('source','')}</div>
            </div>"""
        events_ph.markdown(f"""
        <div style="background:#ffffff;border:1.5px solid #86efac;border-radius:12px;
                    padding:16px;margin-top:12px;">
            <div style="font-size:13px;font-weight:600;color:#16a34a;margin-bottom:8px;">최근 이벤트</div>
            {items_html}
        </div>
        """, unsafe_allow_html=True)
    st.stop()


# ── 실행 중 ─────────────────────────────────────────────
is_rtsp     = st.session_state.is_rtsp
rtsp_reader = st.session_state.rtsp_reader
vs          = st.session_state.video_source
detector    = st.session_state.detector

if is_rtsp and (rtsp_reader is None or not rtsp_reader.is_alive):
    stop_all()
    st.warning("RTSP 스레드가 종료됐습니다. 다시 시작하세요.")
    st.stop()

if not is_rtsp and (vs is None or not vs.is_open()):
    stop_all()
    st.warning("영상 소스 연결이 끊어졌습니다. 다시 시작하세요.")
    st.stop()

roi_polygon = load_roi(st.session_state.source_name)

while st.session_state.running:
    if is_rtsp:
        frame = rtsp_reader.get_latest_frame()
        ret   = frame is not None
        if not ret and rtsp_reader.error:
            stop_all()
            st.error(f"RTSP 오류: {rtsp_reader.error}")
            break
    else:
        ret, frame = vs.read_frame()
        if not ret:
            vs.reset()
            continue

    if not ret or frame is None:
        frame = st.session_state.last_good_frame
        if frame is None:
            time.sleep(0.02)
            continue
        is_new_frame = False
    else:
        st.session_state.last_good_frame = frame
        is_new_frame = True

    st.session_state.frame_idx += 1
    frame_idx = st.session_state.frame_idx

    if is_new_frame and (frame_idx % FRAME_SKIP == 0 or frame_idx == 1):
        detections = detector.detect(frame, conf=conf_threshold)
        st.session_state.last_detections = detections
    else:
        detections = st.session_state.last_detections

    danger_result = check_danger(detections, roi_polygon)
    is_danger     = danger_result["is_danger"]

    now = time.time()
    event_triggered = False
    if is_danger and not st.session_state.prev_danger:
        if now - st.session_state.last_event_ts > 15.0:
            event_triggered                = True
            st.session_state.last_event_ts = now
            st.session_state.alert_msg     = "위험! 보행자 감지"
            st.session_state.alert_expires = now + 3.0

    st.session_state.prev_danger = is_danger

    annotated = frame.copy()
    annotated = draw_detections(annotated, danger_result, roi_polygon)

    if is_danger:
        cv2.putText(annotated, "!! DANGER - PEDESTRIAN IN ZONE !!",
                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 220), 2, cv2.LINE_AA)

    update_fps()
    src_tag = "RTSP" if is_rtsp else "FILE"
    cv2.putText(annotated,
                f"FPS:{st.session_state.fps_display}  F:{frame_idx}  [{src_tag}]",
                (10, annotated.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1, cv2.LINE_AA)

    # 이벤트 저장 처리
    if event_triggered and not st.session_state.post_recording:
        img_name, _ = save_event_image(annotated, st.session_state.source_name)
        st.session_state.pending_img_name = img_name
        st.session_state.pre_frames       = list(st.session_state.frame_buffer)
        st.session_state.post_frames      = []
        st.session_state.post_recording   = True
        st.session_state.post_rec_start   = now

    if st.session_state.post_recording:
        st.session_state.post_frames.append(annotated.copy())
        if now - st.session_state.post_rec_start >= CLIP_POST_SEC:
            all_frames = st.session_state.pre_frames + st.session_state.post_frames
            clip_name, _ = save_event_clip(deque(all_frames), st.session_state.source_name, fps=MAX_CLIP_FPS)
            log_event(st.session_state.source_name, st.session_state.pending_img_name, clip_name)
            st.session_state.post_recording = False
            st.session_state.pre_frames     = []
            st.session_state.post_frames    = []
            st.session_state.pending_img_name = ""

    st.session_state.frame_buffer.append(annotated.copy())

    display_frame = annotated
    if st.session_state.get("remote_mode", False):
        h_orig, w_orig = display_frame.shape[:2]
        if w_orig > 640:
            ratio = 640 / w_orig
            display_frame = cv2.resize(display_frame, (640, int(h_orig * ratio)), interpolation=cv2.INTER_AREA)

    rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
    frame_ph.image(rgb, channels="RGB", use_container_width=True)

    persons = len(danger_result["all_persons"])
    cars    = len(danger_result["all_cars"])
    roi_ok  = roi_polygon is not None

    info_ph.markdown(f"""
    <div style="display:flex;gap:16px;padding:8px 12px;font-size:12px;color:#6b7280;
                background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;margin-top:6px;">
        <span>👤 사람 <b style="color:#111827;">{persons}</b>명</span>
        <span>🚗 차량 <b style="color:#111827;">{cars}</b>대</span>
        <span>ROI <b style="color:{'#16a34a' if roi_ok else '#d97706'};">{'설정됨' if roi_ok else '미설정'}</b></span>
        <span style="color:#9ca3af;">{st.session_state.source_name}</span>
    </div>
    """, unsafe_allow_html=True)

    # 상태 패널
    if is_danger:
        status_ph.markdown("""
        <div style="background:#fff5f5;border:2px solid #ef4444;border-radius:12px;
                    padding:20px;text-align:center;">
            <div style="font-size:36px;margin-bottom:8px;">🔴</div>
            <div style="font-size:18px;font-weight:700;color:#dc2626;">위험 감지</div>
            <div style="font-size:12px;color:#ef4444;margin-top:4px;">보행자가 위험 구역에 있습니다</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        status_ph.markdown("""
        <div style="background:#f0fdf4;border:2px solid #86efac;border-radius:12px;
                    padding:20px;text-align:center;">
            <div style="font-size:36px;margin-bottom:8px;">🟢</div>
            <div style="font-size:18px;font-weight:700;color:#16a34a;">정상</div>
            <div style="font-size:12px;color:#22c55e;margin-top:4px;">위험 없음</div>
        </div>
        """, unsafe_allow_html=True)

    if now < st.session_state.alert_expires:
        alert_ph.markdown(f"""
        <div style="background:#fff5f5;border:1.5px solid #ef4444;border-radius:8px;
                    padding:10px 14px;margin-top:8px;font-size:13px;color:#dc2626;font-weight:600;">
            🚨 {st.session_state.alert_msg}
        </div>
        """, unsafe_allow_html=True)
    else:
        alert_ph.empty()

    if event_triggered:
        recent = get_recent_events(4)
        if recent:
            items_html = ""
            for ev in recent:
                items_html += f"""
                <div style="padding:7px 0;border-bottom:1px solid #f0fdf4;font-size:11px;">
                    <div style="color:#dc2626;font-weight:600;">● 위험 감지</div>
                    <div style="color:#6b7280;">{ev.get('timestamp','')[:19]}</div>
                </div>"""
            events_ph.markdown(f"""
            <div style="background:#ffffff;border:1.5px solid #86efac;border-radius:10px;
                        padding:14px;margin-top:8px;">
                <div style="font-size:12px;font-weight:600;color:#16a34a;margin-bottom:6px;">최근 이벤트</div>
                {items_html}
            </div>
            """, unsafe_allow_html=True)

    if st.session_state.get("remote_mode", False):
        time.sleep(0.2)
    else:
        time.sleep(0.001 if is_rtsp else 0.020)
