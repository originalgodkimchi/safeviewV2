# pages/2_ROI_설정.py — ROI 위험 구역 설정

import streamlit as st
import cv2
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import DATA_DIR
from core.video_source import VideoSource
from core.roi_manager  import save_roi, load_roi, list_saved_rois

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    LIB_OK = True
except ImportError:
    LIB_OK = False

st.set_page_config(
    page_title="ROI 설정 | SAFE VIEW",
    page_icon="🗺️",
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
}
[data-testid="stMetricValue"] { color: #16a34a !important; font-size: 1.4rem !important; font-weight: 700 !important; }
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

.stSelectbox [data-baseweb="select"] > div {
    background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
}
.stTextInput input {
    background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
}
.stRadio label { color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

if not LIB_OK:
    st.error("❌ `streamlit-image-coordinates` 패키지가 필요합니다.\n\n`pip install streamlit-image-coordinates`")
    st.stop()

DISPLAY_W = 800

def render_frame(frame_bgr, points: list, scale: float) -> Image.Image:
    rgb  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil  = Image.fromarray(rgb)
    orig_h, orig_w = frame_bgr.shape[:2]
    disp_h = int(orig_h * scale)
    pil  = pil.resize((DISPLAY_W, disp_h), Image.LANCZOS)

    if not points:
        return pil

    draw     = ImageDraw.Draw(pil, "RGBA")
    disp_pts = [(int(x * scale), int(y * scale)) for x, y in points]

    if len(disp_pts) >= 3:
        draw.polygon(disp_pts, fill=(22, 163, 74, 50), outline=(22, 163, 74))

    for i in range(len(disp_pts) - 1):
        draw.line([disp_pts[i], disp_pts[i+1]], fill=(22, 163, 74), width=2)

    for i, (px, py) in enumerate(disp_pts):
        r = 8
        draw.ellipse([(px-r, py-r), (px+r, py+r)], fill=(220, 38, 38), outline=(255, 255, 255))
        draw.text((px + 11, py - 9), f"P{i+1}", fill=(255, 255, 255))

    return pil

def get_video_files() -> list:
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR)
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))]


# ── 세션 초기화 ─────────────────────────────────────────
for key, val in [("roi_points", []), ("roi_frame", None),
                 ("last_click", None), ("roi_src_label", "")]:
    if key not in st.session_state:
        st.session_state[key] = val


# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:18px;font-weight:700;color:#15803d;padding:8px 0 16px;
                display:flex;align-items:center;gap:8px;">
        🗺️ <span>ROI 설정</span>
    </div>
    """, unsafe_allow_html=True)

    source_type = st.radio("영상 소스", ["📁 로컬 영상 파일", "📡 RTSP 스트림"])

    selected_source = None
    auto_label      = ""

    if source_type == "📁 로컬 영상 파일":
        files = get_video_files()
        if files:
            chosen          = st.selectbox("파일 선택", files)
            selected_source = os.path.join(DATA_DIR, chosen)
            auto_label      = os.path.splitext(chosen)[0]
        else:
            st.warning("`data/` 폴더에 영상 파일을 넣어주세요.")
    else:
        rtsp = st.text_input("RTSP 주소", placeholder="rtsp://admin:1234@192.168.0.100:554/...")
        if rtsp.startswith("rtsp://"):
            selected_source = rtsp

    label_input = st.text_input(
        "ROI 저장 이름",
        value=st.session_state.roi_src_label or auto_label,
        help="모니터링 페이지의 소스 이름과 같아야 자동 로드됩니다.",
    )
    st.session_state.roi_src_label = label_input

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("📷 기준 프레임 불러오기", type="primary",
                 disabled=selected_source is None, use_container_width=True):
        with st.spinner("프레임 불러오는 중..."):
            vs    = VideoSource(selected_source)
            frame = vs.get_first_frame()
        if frame is not None:
            st.session_state.roi_frame  = frame
            st.session_state.roi_points = []
            st.session_state.last_click = None
            h, w = frame.shape[:2]
            st.success(f"완료 ({w}×{h})")
        else:
            st.error("프레임을 가져올 수 없습니다.")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:13px;font-weight:600;color:#6b7280;margin-bottom:8px;">저장된 ROI</div>', unsafe_allow_html=True)
    saved = list_saved_rois()
    if saved:
        sel = st.selectbox("불러올 ROI", ["— 선택 —"] + saved, label_visibility="collapsed")
        if sel != "— 선택 —":
            pts = load_roi(sel)
            if pts is not None:
                for i, p in enumerate(pts):
                    st.caption(f"P{i+1}: ({p[0]}, {p[1]})")
    else:
        st.caption("저장된 ROI 없음")


# ── 메인 화면 ────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
    <div style="background:#dcfce7;border-radius:10px;padding:8px 10px;font-size:20px;line-height:1;">🗺️</div>
    <div style="font-size:20px;font-weight:700;color:#15803d;">위험 구역 설정</div>
</div>
<div style="color:#6b7280;font-size:14px;margin-bottom:16px;
            background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 14px;">
    💡 영상 위를 클릭해서 꼭짓점을 추가하세요. <b style="color:#16a34a;">3개 이상</b> 찍으면 위험 구역 폴리곤이 생성됩니다.
</div>
""", unsafe_allow_html=True)

frame = st.session_state.roi_frame

if frame is None:
    st.markdown("""
    <div style="background:#ffffff;border:2px dashed #86efac;border-radius:14px;
                padding:80px 20px;text-align:center;">
        <div style="font-size:48px;margin-bottom:12px;">🖼️</div>
        <div style="color:#6b7280;font-size:15px;">
            왼쪽 패널에서 소스를 선택하고<br>
            <b style="color:#16a34a;">📷 기준 프레임 불러오기</b>를 누르세요
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

orig_h, orig_w = frame.shape[:2]
scale = DISPLAY_W / orig_w

# 컨트롤 바
ctrl1, ctrl2, ctrl3, info_col = st.columns([1, 1, 1, 3])

if ctrl1.button("↩ 마지막 점 취소", use_container_width=True):
    if st.session_state.roi_points:
        st.session_state.roi_points.pop()
        st.session_state.last_click = None
    st.rerun()

if ctrl2.button("🗑 전체 초기화", use_container_width=True):
    st.session_state.roi_points = []
    st.session_state.last_click = None
    st.rerun()

save_clicked = ctrl3.button("💾 ROI 저장", type="primary", use_container_width=True)

pts = st.session_state.roi_points
can_save = len(pts) >= 3 and bool(st.session_state.roi_src_label)

info_col.markdown(f"""
<div style="display:flex;gap:20px;align-items:center;height:100%;font-size:13px;padding-top:6px;">
    <span style="color:#374151;">꼭짓점 <b style="color:#16a34a;">{len(pts)}</b>개</span>
    <span style="color:#374151;">저장 이름: <b style="color:#16a34a;">{st.session_state.roi_src_label or '(미입력)'}</b></span>
    <span style="color:{'#16a34a' if can_save else '#d97706'};font-weight:600;">
        {'✅ 저장 가능' if can_save else '⚠ 3개 이상 + 이름 필요'}
    </span>
</div>
""", unsafe_allow_html=True)

# 캔버스
pil_img = render_frame(frame, pts, scale)
click   = streamlit_image_coordinates(pil_img, key="roi_click")

if click is not None:
    new_coord = (click["x"], click["y"])
    if new_coord != st.session_state.last_click:
        st.session_state.last_click = new_coord
        orig_x = int(click["x"] / scale)
        orig_y = int(click["y"] / scale)
        st.session_state.roi_points.append([orig_x, orig_y])
        st.rerun()

# 꼭짓점 좌표 표시
if pts:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;font-weight:600;color:#6b7280;margin-bottom:8px;">꼭짓점 좌표 (원본 기준)</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(pts), 8))
    for i, p in enumerate(pts):
        cols[i % 8].markdown(f"""
        <div style="background:#ffffff;border:1.5px solid #86efac;border-radius:8px;
                    padding:8px;text-align:center;font-size:12px;
                    box-shadow:0 1px 3px rgba(22,163,74,0.08);">
            <div style="color:#dc2626;font-weight:700;">P{i+1}</div>
            <div style="color:#374151;">{p[0]}, {p[1]}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown('<div style="color:#6b7280;font-size:13px;margin-top:8px;">아직 찍은 꼭짓점이 없습니다. 위 영상을 클릭하세요.</div>', unsafe_allow_html=True)

# 저장 처리
if save_clicked:
    label = st.session_state.roi_src_label
    if not label:
        st.error("사이드바에서 ROI 저장 이름을 입력하세요.")
    elif len(pts) < 3:
        st.error("꼭짓점이 3개 이상이어야 합니다.")
    else:
        path = save_roi(label, pts)
        st.markdown(f"""
        <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:12px;
                    padding:16px 20px;margin-top:8px;">
            <div style="font-size:15px;font-weight:700;color:#16a34a;margin-bottom:8px;">✅ ROI 저장 완료</div>
            <div style="font-size:13px;color:#6b7280;">
                이름: <b style="color:#111827;">{label}</b> &nbsp;|&nbsp;
                꼭짓점: <b style="color:#111827;">{len(pts)}개</b> &nbsp;|&nbsp;
                파일: <b style="color:#111827;">{path}</b>
            </div>
            <div style="font-size:13px;color:#6b7280;margin-top:6px;">
                모니터링 페이지에서 <b style="color:#16a34a;">{label}</b> 소스를 선택하면 자동 적용됩니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
