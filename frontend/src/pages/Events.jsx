import { useState, useEffect } from 'react'
import { api, API_BASE } from '../config'

const TABS = ['사진', '영상', '상세정보']

export default function Events() {
  const [events, setEvents] = useState([])
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [activeTab, setActiveTab] = useState({})
  const [loading, setLoading] = useState(false)

  // 날짜 목록 로드
  useEffect(() => {
    api.get('/api/events/dates').then(r => {
      setDates(r.data.dates || [])
    }).catch(() => {})
  }, [])

  // 이벤트 로드 (날짜 필터 포함)
  useEffect(() => {
    setLoading(true)
    const params = selectedDate ? { date: selectedDate } : {}
    api.get('/api/events', { params })
      .then(r => setEvents(r.data.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [selectedDate])

  const toggleExpand = (id) => {
    setExpandedId(prev => prev === id ? null : id)
    setActiveTab(prev => ({ ...prev, [id]: prev[id] || '사진' }))
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">이벤트 기록</h1>
        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          총 {events.length}건
        </span>
      </div>

      {/* 날짜 필터 */}
      <div className="bg-white rounded-2xl border border-sv-border p-5 shadow-sm mb-5">
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">날짜 선택</label>
            <input
              type="date"
              value={selectedDate}
              onChange={e => setSelectedDate(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sv-green"
            />
          </div>
          {selectedDate && (
            <button
              onClick={() => setSelectedDate('')}
              className="mt-5 text-xs text-gray-400 hover:text-gray-600 border border-gray-200 px-3 py-2 rounded-lg"
            >
              필터 초기화
            </button>
          )}

          {/* 이벤트 있는 날짜 뱃지 */}
          {dates.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4 ml-auto">
              {dates.slice(0, 7).map(d => (
                <button
                  key={d}
                  onClick={() => setSelectedDate(d)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    selectedDate === d
                      ? 'bg-sv-green text-white border-sv-green'
                      : 'border-sv-border text-gray-600 hover:border-sv-green'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 이벤트 목록 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">로딩 중...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-sv-border shadow-sm">
          <svg className="w-16 h-16 mx-auto mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="text-gray-400 text-sm">이벤트가 없습니다</p>
          {selectedDate && <p className="text-xs text-gray-300 mt-1">{selectedDate} 날짜에 이벤트가 없습니다</p>}
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((ev, i) => {
            const id = `${i}-${ev.timestamp}`
            const isOpen = expandedId === id
            const tab = activeTab[id] || '사진'

            return (
              <div key={id} className="bg-white rounded-2xl border border-sv-border shadow-sm overflow-hidden">
                {/* 카드 헤더 */}
                <button
                  onClick={() => toggleExpand(id)}
                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5 bg-red-100 text-red-700 px-2.5 py-0.5 rounded-full text-xs font-medium">
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                      위험 감지
                    </span>
                    <span className="text-sm text-gray-700 font-medium">{ev.timestamp}</span>
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded truncate max-w-xs">
                      {ev.source}
                    </span>
                  </div>
                  <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* 펼쳐진 내용 */}
                {isOpen && (
                  <div className="border-t border-sv-border">
                    {/* 탭 */}
                    <div className="flex border-b border-sv-border px-5">
                      {TABS.map(t => (
                        <button
                          key={t}
                          onClick={() => setActiveTab(prev => ({ ...prev, [id]: t }))}
                          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                            tab === t
                              ? 'border-sv-green text-sv-green'
                              : 'border-transparent text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>

                    <div className="p-5">
                      {tab === '사진' && (
                        <EventImageTab ev={ev} />
                      )}
                      {tab === '영상' && (
                        <EventVideoTab ev={ev} />
                      )}
                      {tab === '상세정보' && (
                        <EventDetailTab ev={ev} />
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function EventImageTab({ ev }) {
  if (!ev.image_file) {
    return <p className="text-sm text-gray-400 text-center py-8">이미지 없음</p>
  }
  return (
    <div className="flex justify-center">
      <img
        src={`${API_BASE}/events-files/${ev.image_file}`}
        alt="이벤트 이미지"
        className="max-w-full max-h-80 rounded-xl border border-sv-border object-contain"
        onError={e => { e.target.style.display = 'none' }}
      />
    </div>
  )
}

function EventVideoTab({ ev }) {
  if (!ev.clip_file) {
    return <p className="text-sm text-gray-400 text-center py-8">클립 없음</p>
  }
  return (
    <div className="flex justify-center">
      <video
        src={`${API_BASE}/events-files/${ev.clip_file}`}
        controls
        className="max-w-full max-h-80 rounded-xl border border-sv-border"
      />
    </div>
  )
}

function EventDetailTab({ ev }) {
  const rows = [
    { label: '발생 시각', value: ev.timestamp },
    { label: '소스', value: ev.source },
    { label: '상태', value: ev.status || '위험' },
    { label: '이미지 파일', value: ev.image_file || '-' },
    { label: '클립 파일', value: ev.clip_file || '-' },
  ]
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <tbody className="divide-y divide-gray-100">
          {rows.map(r => (
            <tr key={r.label}>
              <td className="py-2.5 pr-4 text-gray-500 font-medium w-32 whitespace-nowrap">{r.label}</td>
              <td className="py-2.5 text-gray-700 break-all">{r.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
