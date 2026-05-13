# app.py — 홈 대시보드

import streamlit as st
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import EVENTS_DIR, LOGS_DIR, ROI_DIR, DATA_DIR

st.set_page_config(
    page_title="SAFE VIEW",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

for d in [EVENTS_DIR, LOGS_DIR, ROI_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

/* ── 전체 배경 ── */
[data-testid="stAppViewContainer"] {
    background: #f8fffe;
}
[data-testid="stMain"] {
    background: #f8fffe;
}
[data-testid="stSidebar"] {
    background: #f0fdf4;
    border-right: 2px solid #bbf7d0;
}
[data-testid="stSidebarContent"] {
    background: #f0fdf4;
}

/* ── 텍스트 ── */
body, p, span, div, label { color: #111827; }
h1, h2, h3, h4 { color: #111827; }

/* ── 사이드바 네비게이션 링크 ── */
[data-testid="stSidebarNav"] a {
    color: #374151 !important;
    border-radius: 8px;
    padding: 8px 12px;
    transition: all 0.2s;
    font-weight: 500;
}
[data-testid="stSidebarNav"] a:hover {
    color: #16a34a !important;
    background: #dcfce7 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #15803d !important;
    background: #bbf7d0 !important;
    font-weight: 600;
}

/* ── hr ── */
hr { border-color: #d1fae5 !important; }

/* ── metric ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1.5px solid #86efac;
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 1px 4px rgba(22,163,74,0.08);
}
[data-testid="stMetricValue"] {
    color: #16a34a !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
    font-weight: 500 !important;
}

/* ── 버튼 ── */
.stButton > button {
    background: #ffffff;
    color: #374151;
    border: 1.5px solid #d1d5db;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #f0fdf4;
    border-color: #16a34a;
    color: #16a34a;
}
.stButton > button[kind="primary"] {
    background: #16a34a;
    border-color: #16a34a;
    color: #ffffff;
    font-weight: 600;
}
.stButton > button[kind="primary"]:hover {
    background: #15803d;
    border-color: #15803d;
}
</style>
""", unsafe_allow_html=True)

# ── 헤더 ──
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;
            padding:20px 24px;background:#ffffff;border-radius:16px;
            border:1.5px solid #bbf7d0;box-shadow:0 2px 8px rgba(22,163,74,0.08);">
    <div style="background:#dcfce7;border-radius:14px;padding:12px;font-size:36px;line-height:1;">🛡️</div>
    <div>
        <div style="font-size:26px;font-weight:700;color:#15803d;letter-spacing:-0.5px;">SAFE VIEW</div>
        <div style="font-size:13px;color:#6b7280;margin-top:2px;">주차 차량 사각지대 보행자 위험 감지 시스템</div>
    </div>
    <div style="margin-left:auto;display:flex;align-items:center;gap:8px;
                background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:6px 14px;">
        <div style="width:8px;height:8px;background:#22c55e;border-radius:50%;"></div>
        <span style="font-size:12px;color:#16a34a;font-weight:600;">시스템 정상</span>
    </div>
</div>
<div style="margin:12px 0 20px;border-bottom:2px solid #d1fae5;"></div>
""", unsafe_allow_html=True)

# ── 상태 메트릭 ──
roi_count   = len([f for f in os.listdir(ROI_DIR)    if f.endswith(".json")]) if os.path.exists(ROI_DIR)    else 0
event_count = len([f for f in os.listdir(EVENTS_DIR) if f.endswith(".jpg")])  if os.path.exists(EVENTS_DIR) else 0
data_count  = len([f for f in os.listdir(DATA_DIR)   if f.lower().endswith((".mp4",".avi",".mov",".mkv"))]) if os.path.exists(DATA_DIR) else 0

m1, m2, m3 = st.columns(3)
m1.metric("저장된 ROI",  f"{roi_count}개")
m2.metric("감지 이벤트", f"{event_count}건")
m3.metric("샘플 영상",   f"{data_count}개")

st.markdown("<br>", unsafe_allow_html=True)

# ── 위험 판단 규칙 & 사용 방법 ──
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("""
<div style="background:#ffffff;border:1.5px solid #86efac;border-radius:14px;padding:24px;
            box-shadow:0 2px 8px rgba(22,163,74,0.06);">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:18px;">
        <div style="background:#dcfce7;border-radius:8px;padding:6px 8px;font-size:16px;">⚠️</div>
        <div style="font-size:16px;font-weight:700;color:#15803d;">위험 판단 규칙</div>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background:#f0fdf4;">
                <th style="text-align:left;padding:10px 14px;color:#6b7280;font-weight:600;
                           border-radius:8px 0 0 0;border-bottom:2px solid #d1fae5;">조건</th>
                <th style="text-align:center;padding:10px 14px;color:#6b7280;font-weight:600;
                           border-radius:0 8px 0 0;border-bottom:2px solid #d1fae5;">상태</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding:10px 14px;color:#374151;border-bottom:1px solid #f0fdf4;">아무것도 없음</td>
                <td style="text-align:center;padding:10px 14px;border-bottom:1px solid #f0fdf4;">
                    <span style="background:#dcfce7;color:#16a34a;font-weight:600;
                                 border-radius:20px;padding:3px 10px;font-size:12px;">● 정상</span></td>
            </tr>
            <tr style="background:#fafafa;">
                <td style="padding:10px 14px;color:#374151;border-bottom:1px solid #f0fdf4;">사람만 있음</td>
                <td style="text-align:center;padding:10px 14px;border-bottom:1px solid #f0fdf4;">
                    <span style="background:#dcfce7;color:#16a34a;font-weight:600;
                                 border-radius:20px;padding:3px 10px;font-size:12px;">● 정상</span></td>
            </tr>
            <tr>
                <td style="padding:10px 14px;color:#374151;border-bottom:1px solid #f0fdf4;">차량만 있음</td>
                <td style="text-align:center;padding:10px 14px;border-bottom:1px solid #f0fdf4;">
                    <span style="background:#dcfce7;color:#16a34a;font-weight:600;
                                 border-radius:20px;padding:3px 10px;font-size:12px;">● 정상</span></td>
            </tr>
            <tr style="background:#fafafa;">
                <td style="padding:10px 14px;color:#374151;border-bottom:1px solid #f0fdf4;">사람 + 차량, 사람이 ROI 밖</td>
                <td style="text-align:center;padding:10px 14px;border-bottom:1px solid #f0fdf4;">
                    <span style="background:#dcfce7;color:#16a34a;font-weight:600;
                                 border-radius:20px;padding:3px 10px;font-size:12px;">● 정상</span></td>
            </tr>
            <tr style="background:#fff5f5;">
                <td style="padding:10px 14px;color:#dc2626;font-weight:600;border-radius:0 0 0 8px;">사람 + 차량, 사람이 ROI 안</td>
                <td style="text-align:center;padding:10px 14px;border-radius:0 0 8px 0;">
                    <span style="background:#fee2e2;color:#dc2626;font-weight:700;
                                 border-radius:20px;padding:3px 10px;font-size:12px;">● 위험</span></td>
            </tr>
        </tbody>
    </table>
</div>
""", unsafe_allow_html=True)

with col_right:
    st.markdown("""
<div style="background:#ffffff;border:1.5px solid #86efac;border-radius:14px;padding:24px;
            box-shadow:0 2px 8px rgba(22,163,74,0.06);height:100%;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:18px;">
        <div style="background:#dcfce7;border-radius:8px;padding:6px 8px;font-size:16px;">🚀</div>
        <div style="font-size:16px;font-weight:700;color:#15803d;">시작하기</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="display:flex;align-items:flex-start;gap:14px;">
            <div style="background:#16a34a;color:#ffffff;font-weight:700;border-radius:50%;
                        width:30px;height:30px;display:flex;align-items:center;justify-content:center;
                        flex-shrink:0;font-size:13px;box-shadow:0 2px 6px rgba(22,163,74,0.3);">1</div>
            <div>
                <div style="color:#111827;font-weight:600;font-size:14px;">ROI 설정</div>
                <div style="color:#6b7280;font-size:13px;margin-top:2px;">왼쪽 메뉴에서 ROI 설정 페이지로 이동해<br>위험 구역을 먼저 지정하세요.</div>
            </div>
        </div>
        <div style="border-left:2px dashed #bbf7d0;height:12px;margin-left:14px;"></div>
        <div style="display:flex;align-items:flex-start;gap:14px;">
            <div style="background:#16a34a;color:#ffffff;font-weight:700;border-radius:50%;
                        width:30px;height:30px;display:flex;align-items:center;justify-content:center;
                        flex-shrink:0;font-size:13px;box-shadow:0 2px 6px rgba(22,163,74,0.3);">2</div>
            <div>
                <div style="color:#111827;font-weight:600;font-size:14px;">모니터링 시작</div>
                <div style="color:#6b7280;font-size:13px;margin-top:2px;">영상 파일 또는 RTSP 주소를 선택하고<br>감지를 시작하세요.</div>
            </div>
        </div>
        <div style="border-left:2px dashed #bbf7d0;height:12px;margin-left:14px;"></div>
        <div style="display:flex;align-items:flex-start;gap:14px;">
            <div style="background:#16a34a;color:#ffffff;font-weight:700;border-radius:50%;
                        width:30px;height:30px;display:flex;align-items:center;justify-content:center;
                        flex-shrink:0;font-size:13px;box-shadow:0 2px 6px rgba(22,163,74,0.3);">3</div>
            <div>
                <div style="color:#111827;font-weight:600;font-size:14px;">이벤트 확인</div>
                <div style="color:#6b7280;font-size:13px;margin-top:2px;">위험 감지 시 자동 저장된 이미지·영상을<br>이벤트 다시보기에서 확인하세요.</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
