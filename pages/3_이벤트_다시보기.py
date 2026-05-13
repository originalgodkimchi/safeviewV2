# pages/3_이벤트_다시보기.py — 이벤트 기록 조회

import streamlit as st
import os
import sys
import csv
import subprocess
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import EVENTS_DIR, LOG_FILE

st.set_page_config(
    page_title="이벤트 | SAFE VIEW",
    page_icon="📋",
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

.stTabs [data-baseweb="tab-list"] {
    background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;
}
.stTabs [data-baseweb="tab"] { color: #6b7280 !important; font-weight: 500; }
.stTabs [aria-selected="true"] { color: #16a34a !important; font-weight: 600; border-bottom-color: #16a34a !important; }

.stDateInput input {
    background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
}

/* expander */
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    background: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


# ── 유틸 함수 ────────────────────────────────────────────
def load_all_events():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def get_events_by_date(events, target: date):
    s = target.strftime("%Y-%m-%d")
    return [ev for ev in events if ev.get("timestamp", "").startswith(s)]

def get_dates_with_events(events):
    dates = set()
    for ev in events:
        ts = ev.get("timestamp", "")
        if len(ts) >= 10:
            try:
                dates.add(datetime.strptime(ts[:10], "%Y-%m-%d").date())
            except ValueError:
                pass
    return dates


CONVERTED_DIR = os.path.join(EVENTS_DIR, "_converted")
os.makedirs(CONVERTED_DIR, exist_ok=True)

def get_playable_video(clip_path: str) -> str | None:
    filename = os.path.basename(clip_path)
    converted_path = os.path.join(CONVERTED_DIR, filename)
    if os.path.exists(converted_path):
        return converted_path
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    except ImportError:
        return None
    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", clip_path,
             "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-movflags", "+faststart", "-an", converted_path],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and os.path.exists(converted_path):
            return converted_path
    except Exception:
        pass
    return None


# ── 데이터 로드 ──────────────────────────────────────────
all_events  = load_all_events()
event_dates = get_dates_with_events(all_events)

if "sel_date" not in st.session_state:
    st.session_state.sel_date = date.today()


# ── 사이드바 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:18px;font-weight:700;color:#15803d;padding:8px 0 16px;
                display:flex;align-items:center;gap:8px;">
        📋 <span>이벤트 조회</span>
    </div>
    """, unsafe_allow_html=True)

    new_date = st.date_input("날짜 선택", value=st.session_state.sel_date)
    if new_date != st.session_state.sel_date:
        st.session_state.sel_date = new_date
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:13px;font-weight:600;color:#6b7280;margin-bottom:12px;">통계</div>', unsafe_allow_html=True)
    st.metric("전체 이벤트", f"{len(all_events)}건")
    st.metric("기록된 날짜", f"{len(event_dates)}일")

    if event_dates:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px;font-weight:600;color:#6b7280;margin-bottom:8px;">이벤트 있는 날짜</div>', unsafe_allow_html=True)
        for d in sorted(event_dates, reverse=True)[:10]:
            cnt = len(get_events_by_date(all_events, d))
            if st.button(f"● {d.strftime('%Y-%m-%d')}  ({cnt}건)", key=f"sb_{d}", use_container_width=True):
                st.session_state.sel_date = d
                st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    if os.path.exists(EVENTS_DIR):
        files = [f for f in os.listdir(EVENTS_DIR) if not f.startswith("_")]
        total = sum(
            os.path.getsize(os.path.join(EVENTS_DIR, f))
            for f in files if os.path.isfile(os.path.join(EVENTS_DIR, f))
        )
        st.markdown('<div style="font-size:13px;font-weight:600;color:#6b7280;margin-bottom:8px;">저장 용량</div>', unsafe_allow_html=True)
        imgs  = len([f for f in files if f.endswith(".jpg")])
        clips = len([f for f in files if f.endswith(".mp4")])
        st.caption(f"이미지 {imgs}개 · 클립 {clips}개 · {total/(1024*1024):.1f} MB")


# ── 메인 화면 ────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <div style="background:#dcfce7;border-radius:10px;padding:8px 10px;font-size:20px;line-height:1;">📋</div>
    <div style="font-size:20px;font-weight:700;color:#15803d;">이벤트 다시보기</div>
</div>
""", unsafe_allow_html=True)

if not all_events:
    st.markdown("""
    <div style="background:#ffffff;border:2px dashed #86efac;border-radius:14px;
                padding:60px 20px;text-align:center;">
        <div style="font-size:48px;margin-bottom:12px;">📭</div>
        <div style="color:#6b7280;font-size:15px;">저장된 이벤트가 없습니다.<br>모니터링에서 위험 감지가 발생하면 여기에 기록됩니다.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

sel = st.session_state.sel_date

# 선택 날짜 헤더
day_events = get_events_by_date(all_events, sel)
has_today  = sel in event_dates

st.markdown(f"""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
    <div style="background:#ffffff;
                border:2px solid {'#ef4444' if has_today else '#e5e7eb'};
                border-radius:12px;padding:14px 22px;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <div style="font-size:20px;font-weight:700;color:{'#dc2626' if has_today else '#6b7280'};">
            {sel.strftime('%Y년 %m월 %d일')}
        </div>
        <div style="font-size:13px;color:#6b7280;margin-top:2px;">
            {'🚨 ' + str(len(day_events)) + '건의 위험 이벤트' if day_events else '이벤트 없음'}
        </div>
    </div>
    {f'<div style="background:#fee2e2;border:1px solid #fca5a5;border-radius:8px;padding:8px 16px;font-size:13px;color:#dc2626;font-weight:600;">위험 {len(day_events)}건</div>' if day_events else ''}
</div>
""", unsafe_allow_html=True)

if not day_events:
    st.markdown(f"""
    <div style="background:#ffffff;border:1.5px solid #e5e7eb;border-radius:12px;
                padding:40px 20px;text-align:center;">
        <div style="font-size:32px;margin-bottom:8px;">📅</div>
        <div style="color:#6b7280;font-size:14px;">
            {sel.strftime('%Y-%m-%d')}에 기록된 이벤트가 없습니다.<br>
            왼쪽 패널에서 이벤트가 있는 날짜를 선택하세요.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 이벤트 카드 목록
for idx, ev in enumerate(day_events):
    timestamp = ev.get("timestamp", "")
    source    = ev.get("source", "")
    img_file  = ev.get("image_file", "")
    clip_file = ev.get("clip_file", "")
    time_str  = timestamp[11:19] if len(timestamp) >= 19 else timestamp

    img_path = os.path.join(EVENTS_DIR, img_file) if img_file else ""
    has_img  = bool(img_file) and os.path.exists(img_path)

    # 카드 헤더
    st.markdown(f"""
    <div style="background:#ffffff;border:1.5px solid #fca5a5;border-radius:10px;
                padding:14px 18px;margin-bottom:2px;
                display:flex;align-items:center;gap:16px;
                box-shadow:0 1px 3px rgba(220,38,38,0.08);">
        <div style="background:#fee2e2;border:1px solid #fca5a5;border-radius:6px;
                    padding:4px 12px;font-size:12px;color:#dc2626;font-weight:700;flex-shrink:0;">
            🚨 위험 감지
        </div>
        <div style="font-size:15px;font-weight:600;color:#111827;">{time_str}</div>
        <div style="font-size:13px;color:#6b7280;">소스: {source}</div>
        <div style="margin-left:auto;font-size:12px;color:#9ca3af;">#{idx+1}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"  상세 보기 — {time_str}", expanded=False):
        tab_img, tab_clip, tab_info = st.tabs(["사진", "영상 클립", "상세 정보"])

        with tab_img:
            if has_img:
                st.image(img_path, caption=img_file, use_container_width=True)
            else:
                st.markdown('<div style="color:#6b7280;padding:20px;text-align:center;">저장된 이미지 없음</div>', unsafe_allow_html=True)

        with tab_clip:
            if clip_file:
                clip_path = os.path.join(EVENTS_DIR, clip_file)
                if os.path.exists(clip_path):
                    with st.spinner("영상 변환 중..."):
                        playable = get_playable_video(clip_path)
                    if playable:
                        with open(playable, "rb") as vf:
                            st.video(vf.read())
                    else:
                        st.warning("브라우저 재생 변환에 실패했습니다.")
                        with open(clip_path, "rb") as vf:
                            st.download_button("💾 원본 다운로드", data=vf,
                                               file_name=clip_file, mime="video/mp4",
                                               key=f"dl_{idx}")
                else:
                    st.markdown('<div style="color:#6b7280;padding:20px;text-align:center;">클립 파일 없음</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#6b7280;padding:20px;text-align:center;">저장된 클립 없음</div>', unsafe_allow_html=True)

        with tab_info:
            st.markdown(f"""
<div style="background:#f8fffe;border:1.5px solid #d1fae5;border-radius:10px;padding:16px;font-size:13px;">
    <div style="display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;">
        <span style="color:#6b7280;font-weight:500;">시간</span>
        <span style="color:#111827;">{timestamp}</span>
        <span style="color:#6b7280;font-weight:500;">소스</span>
        <span style="color:#111827;">{source}</span>
        <span style="color:#6b7280;font-weight:500;">상태</span>
        <span style="background:#fee2e2;color:#dc2626;font-weight:700;
                     border-radius:20px;padding:2px 10px;font-size:12px;display:inline-block;">위험 감지</span>
        <span style="color:#6b7280;font-weight:500;">이미지</span>
        <span style="color:#111827;">{img_file or '없음'}</span>
        <span style="color:#6b7280;font-weight:500;">클립</span>
        <span style="color:#111827;">{clip_file or '없음'}</span>
    </div>
</div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
