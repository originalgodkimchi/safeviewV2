import { useState, useEffect, useRef } from 'react'
import { api, API_BASE, getWsUrl } from '../config'

export default function Monitoring() {
  const [videos, setVideos] = useState([])
  const [sourceType, setSourceType] = useState('file')
  const [selectedFile, setSelectedFile] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  const [rtspShow, setRtspShow] = useState(false)
  const [sourceName, setSourceName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [conf, setConf] = useState(0.4)
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [recentEvents, setRecentEvents] = useState([])
  const [errorMsg, setErrorMsg] = useState('')
  const prevRunningRef = useRef(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [remoteMode, setRemoteMode] = useState(false)
  const wsRef = useRef(null)
  const imgRef = useRef(null)
  const videoContainerRef = useRef(null)

  // 영상 목록 로드
  useEffect(() => {
    api.get('/api/roi/videos/list')
      .then(r => {
        setVideos(r.data.videos || [])
        if (r.data.videos?.length > 0) {
          setSelectedFile(r.data.videos[0])
          setSourceName(r.data.videos[0])
        }
      })
      .catch(() => {})
  }, [])

  // WebSocket 연결
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          setStatus(data)
          // 실행 중이었다가 멈춘 경우 에러 메시지 표시
          if (prevRunningRef.current && !data.running && data.error) {
            setErrorMsg(data.error)
          }
          prevRunningRef.current = data.running
          setRunning(data.running)
          if (data.recent_events) setRecentEvents(data.recent_events)
        } catch {}
      }

      ws.onclose = () => {
        // 3초 후 재연결
        setTimeout(connect, 3000)
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const handleStart = async () => {
    const sourcePath = sourceType === 'file' ? selectedFile : rtspUrl
    if (!sourcePath) return

    try {
      await api.post('/api/monitoring/start', {
        source_type: sourceType,
        source_path: sourcePath,
        source_name: sourceName.trim() || sourcePath,
        conf,
      })
      setRunning(true)
    } catch (e) {
      alert('시작 실패: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleStop = async () => {
    await api.post('/api/monitoring/stop')
    setRunning(false)
  }

  const handleRemoteMode = async (enabled) => {
    await api.post(`/api/monitoring/remote-mode?enabled=${enabled}`)
    setRemoteMode(enabled)
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/api/videos/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const r = await api.get('/api/roi/videos/list')
      setVideos(r.data.videos || [])
      setSelectedFile(file.name)
      setSourceName(file.name)
    } catch (e) {
      alert('업로드 실패: ' + (e.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  // 전체화면 이벤트 감지
  useEffect(() => {
    const onChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      videoContainerRef.current?.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  const isDanger = status?.is_danger

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">실시간 모니터링</h1>

      <div className="grid grid-cols-12 gap-5">
        {/* 좌측 컨트롤 패널 */}
        <div className="col-span-3 space-y-4">
          <div className="bg-white rounded-2xl border border-sv-border p-5 shadow-sm">
            <h2 className="font-semibold text-gray-700 mb-4">영상 소스 설정</h2>

            {/* 소스 타입 */}
            <div className="flex rounded-lg overflow-hidden border border-sv-border mb-4">
              <button
                onClick={() => setSourceType('file')}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  sourceType === 'file' ? 'bg-sv-green text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                파일
              </button>
              <button
                onClick={() => setSourceType('rtsp')}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  sourceType === 'rtsp' ? 'bg-sv-green text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                RTSP
              </button>
            </div>

            {sourceType === 'file' ? (
              <div className="mb-4">
                <label className="block text-xs font-medium text-gray-500 mb-1.5">영상 파일 선택</label>
                {videos.length > 0 ? (
                  <select
                    value={selectedFile}
                    onChange={e => { setSelectedFile(e.target.value); setSourceName(e.target.value) }}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sv-green mb-2"
                  >
                    {videos.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                ) : (
                  <p className="text-xs text-gray-400 bg-gray-50 rounded-lg p-3 mb-2">
                    data/ 폴더에 영상 파일이 없습니다
                  </p>
                )}
                <label className={`flex items-center justify-center gap-2 w-full border border-dashed border-gray-300 rounded-lg py-2 text-xs text-gray-500 cursor-pointer hover:border-sv-green hover:text-sv-green transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {uploading ? '업로드 중...' : '영상 파일 업로드'}
                  <input type="file" accept=".mp4,.avi,.mkv,.mov,.wmv,.webm" className="hidden" onChange={handleUpload} />
                </label>
              </div>
            ) : (
              <div className="mb-4">
                <label className="block text-xs font-medium text-gray-500 mb-1.5">RTSP 주소</label>
                <div className="relative">
                  <input
                    type={rtspShow ? 'text' : 'password'}
                    value={rtspUrl}
                    onChange={e => setRtspUrl(e.target.value)}
                    placeholder="rtsp://user:pass@ip:port/path"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 pr-9 text-sm focus:outline-none focus:border-sv-green"
                  />
                  <button
                    type="button"
                    onClick={() => setRtspShow(s => !s)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {rtspShow ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* 소스 이름 (ROI 매칭용) */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                소스 이름
                <span className="ml-1 text-gray-400 font-normal">(ROI 설정과 일치해야 함)</span>
              </label>
              <input
                type="text"
                value={sourceName}
                onChange={e => setSourceName(e.target.value)}
                placeholder="예: cctv_1"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sv-green"
              />
            </div>

            {/* 신뢰도 슬라이더 */}
            <div className="mb-5">
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-medium text-gray-500">감지 신뢰도</label>
                <span className="text-xs font-bold text-sv-green">{conf.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.1" max="0.9" step="0.05"
                value={conf}
                onChange={e => setConf(parseFloat(e.target.value))}
                className="w-full accent-sv-green"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                <span>0.1 (민감)</span>
                <span>0.9 (정밀)</span>
              </div>
            </div>

            {/* 원격 모드 */}
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">원격 모드</p>
                <p className="text-xs text-gray-400">640px · 5FPS (cloudflared 권장)</p>
              </div>
              <button
                onClick={() => handleRemoteMode(!remoteMode)}
                className={`relative w-11 h-6 rounded-full transition-colors ${remoteMode ? 'bg-sv-green' : 'bg-gray-200'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${remoteMode ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>

            {/* 시작/정지 버튼 */}
            {!running ? (
              <button
                onClick={handleStart}
                disabled={sourceType === 'file' && !selectedFile}
                className="w-full bg-sv-green hover:bg-green-700 text-white font-semibold py-2.5 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                모니터링 시작
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2.5 rounded-xl transition-colors"
              >
                정지
              </button>
            )}
          </div>

          {/* 상태 패널 */}
          {status && (
            <div className="bg-white rounded-2xl border border-sv-border p-5 shadow-sm">
              <h2 className="font-semibold text-gray-700 mb-3">시스템 상태</h2>
              <div className="space-y-2 text-sm">
                <StatRow label="FPS" value={status.fps} />
                <StatRow label="프레임" value={status.frame_idx} />
                <StatRow label="ROI" value={status.roi_loaded ? '로드됨' : '미설정'} />
                {status.error && (
                  <p className="text-red-500 text-xs mt-2 bg-red-50 p-2 rounded">{status.error}</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 중앙: 영상 스트림 */}
        <div className="col-span-6 space-y-4">
          {errorMsg && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
              <span className="font-bold shrink-0">연결 실패</span>
              <span>{errorMsg}</span>
              <button onClick={() => setErrorMsg('')} className="ml-auto text-red-400 hover:text-red-600 shrink-0">✕</button>
            </div>
          )}
          <div
            ref={videoContainerRef}
            className="bg-black rounded-2xl overflow-hidden border border-gray-800 shadow-lg aspect-video flex items-center justify-center relative group"
          >
            {running ? (
              <img
                ref={imgRef}
                src={`${API_BASE}/api/stream`}
                alt="MJPEG Stream"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="flex flex-col items-center gap-3 text-gray-500">
                <svg className="w-16 h-16 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                    d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                </svg>
                <p className="text-sm">모니터링 대기 중</p>
                <p className="text-xs text-gray-600">좌측 패널에서 소스를 선택하고 시작하세요</p>
              </div>
            )}

            {/* 위험 오버레이 */}
            {isDanger && (
              <div className="absolute inset-0 border-4 border-red-500 rounded-2xl pointer-events-none animate-pulse" />
            )}

            {/* 전체화면 버튼 */}
            <button
              onClick={toggleFullscreen}
              title={isFullscreen ? '전체화면 종료 (ESC)' : '전체화면'}
              className="absolute top-3 right-3 bg-black/50 hover:bg-black/80 text-white rounded-lg p-2
                         opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10"
            >
              {isFullscreen ? (
                // 축소 아이콘
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M15 9h4.5M15 9V4.5M15 9l5.25-5.25M9 15H4.5M9 15v4.5M9 15l-5.25 5.25M15 15h4.5M15 15v4.5M15 15l5.25 5.25" />
                </svg>
              ) : (
                // 확대 아이콘
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                </svg>
              )}
            </button>
          </div>

          {/* 정보바 */}
          <div className="bg-white rounded-xl border border-sv-border px-5 py-3 flex items-center gap-6 shadow-sm">
            <InfoBadge
              label="사람"
              value={status?.persons ?? 0}
              color={status?.persons > 0 ? 'text-amber-600' : 'text-gray-500'}
            />
            <InfoBadge
              label="차량"
              value={status?.cars ?? 0}
              color={status?.cars > 0 ? 'text-blue-600' : 'text-gray-500'}
            />
            <InfoBadge
              label="ROI"
              value={status?.roi_loaded ? '설정됨' : '미설정'}
              color={status?.roi_loaded ? 'text-sv-green' : 'text-gray-400'}
            />
            <InfoBadge
              label="소스"
              value={maskSource(status?.source_name)}
              color="text-gray-600"
            />
          </div>
        </div>

        {/* 우측: 위험/정상 상태 + 최근 이벤트 */}
        <div className="col-span-3 space-y-4">
          {/* 위험/정상 상태 */}
          <div className={`rounded-2xl border p-5 shadow-sm transition-all ${
            isDanger
              ? 'bg-sv-danger-bg border-red-200'
              : 'bg-sv-mint border-sv-border'
          }`}>
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white text-2xl ${
                isDanger ? 'bg-red-500' : 'bg-sv-green'
              }`}>
                {isDanger ? '!' : '✓'}
              </div>
              <div>
                <div className={`text-lg font-bold ${isDanger ? 'text-red-700' : 'text-sv-green'}`}>
                  {isDanger ? '위험 감지' : '정상'}
                </div>
                <div className="text-xs text-gray-500">
                  {isDanger ? 'ROI 위험 이벤트 감지됨' : '이상 없음'}
                </div>
              </div>
            </div>
          </div>

          {/* 최근 이벤트 */}
          <div className="bg-white rounded-2xl border border-sv-border p-5 shadow-sm">
            <h2 className="font-semibold text-gray-700 mb-3">최근 이벤트</h2>
            {recentEvents.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">이벤트 없음</p>
            ) : (
              <div className="space-y-2">
                {recentEvents.map((ev, i) => (
                  <div key={i} className="bg-red-50 border border-red-100 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                      <span className="text-xs font-medium text-red-700">위험 감지</span>
                    </div>
                    <p className="text-xs text-gray-600">{ev.timestamp}</p>
                    <p className="text-xs text-gray-500 truncate">{maskSource(ev.source)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function maskSource(src) {
  if (!src) return '-'
  // rtsp://user:pass@host... → rtsp://***@host...
  return src.replace(/^(rtsp:\/\/)([^@]+@)/, '$1***@')
}

function StatRow({ label, value }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-800">{value}</span>
    </div>
  )
}

function InfoBadge({ label, value, color }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-sm font-semibold ${color}`}>{value}</span>
    </div>
  )
}

