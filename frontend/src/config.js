import axios from 'axios'

// 개발: VITE_API_URL 미설정 → Vite 프록시가 /api, /ws, /events-files 처리
// 프로덕션: Cloudflare Pages 환경변수에 Render URL 지정
//   예) VITE_API_URL = https://safeview-v2-backend.onrender.com
export const API_BASE = import.meta.env.VITE_API_URL || ''

// 모든 페이지에서 이 인스턴스 사용 (baseURL 자동 적용)
export const api = axios.create({ baseURL: API_BASE })

// WebSocket URL 계산
export function getWsUrl() {
  if (import.meta.env.VITE_API_URL) {
    const base = import.meta.env.VITE_API_URL
    return base.replace(/^http/, 'ws') + '/ws'
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}
