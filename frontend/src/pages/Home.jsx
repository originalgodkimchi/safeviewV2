import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../config'

const dangerRules = [
  { condition: '사람 + 차량 동시 감지', area: 'ROI 영역 내', result: '위험', severity: 'high' },
  { condition: '사람만 감지', area: 'ROI 영역 내/외', result: '정상', severity: 'low' },
  { condition: '차량만 감지', area: 'ROI 영역 내/외', result: '정상', severity: 'low' },
  { condition: 'ROI 미설정', area: '-', result: '판단 불가', severity: 'medium' },
]

const steps = [
  {
    step: '1',
    title: 'ROI 영역 설정',
    desc: '위험 감시 구역(ROI)을 영상 프레임 위에 직접 그려 저장합니다.',
    link: '/roi',
    linkLabel: 'ROI 설정 바로가기',
  },
  {
    step: '2',
    title: '영상 소스 선택',
    desc: '로컬 영상 파일 또는 RTSP 카메라 스트림을 선택합니다.',
    link: '/monitoring',
    linkLabel: '모니터링 시작',
  },
  {
    step: '3',
    title: '이벤트 확인',
    desc: '감지된 위험 이벤트의 사진, 클립, 상세 정보를 확인합니다.',
    link: '/events',
    linkLabel: '이벤트 보기',
  },
]

export default function Home() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.get('/api/events/stats')
      .then(r => setStats(r.data))
      .catch(() => {})
  }, [])

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* 헤더 */}
      <div className="bg-white rounded-2xl border border-sv-border p-8 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-sv-green rounded-2xl flex items-center justify-center shadow">
                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-800">
                  <span className="text-sv-green">SAFE</span>VIEW
                </h1>
                <p className="text-gray-500 text-sm">안전사각지대 감지 시스템</p>
              </div>
            </div>
            <p className="text-gray-600 max-w-xl">
              YOLOv8 기반 실시간 영상 분석으로 사각지대에서 발생하는 사람-차량 위험 상황을 자동으로 감지하고 기록합니다.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 bg-green-50 text-sv-green border border-sv-border px-3 py-1.5 rounded-full text-sm font-medium">
            <span className="w-2 h-2 bg-sv-green rounded-full animate-pulse"></span>
            시스템 정상
          </span>
        </div>

        {/* 메트릭 카드 */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <MetricCard
            icon="roi"
            label="저장된 ROI"
            value={stats ? stats.roi_count : '-'}
            unit="개"
            color="green"
          />
          <MetricCard
            icon="event"
            label="감지 이벤트"
            value={stats ? stats.total : '-'}
            unit="건"
            color="amber"
          />
          <MetricCard
            icon="video"
            label="샘플 영상"
            value={stats ? stats.sample_videos : '-'}
            unit="개"
            color="blue"
          />
        </div>
      </div>

      {/* 위험 판단 규칙 */}
      <div className="bg-white rounded-2xl border border-sv-border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-sv-border">
          <h2 className="font-semibold text-gray-700 text-lg">위험 판단 규칙</h2>
          <p className="text-gray-500 text-sm mt-0.5">ROI 영역 내 감지 조건에 따른 위험 판단 기준</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-sv-mint">
              <tr>
                <th className="px-6 py-3 text-left font-medium text-gray-600">감지 조건</th>
                <th className="px-6 py-3 text-left font-medium text-gray-600">적용 영역</th>
                <th className="px-6 py-3 text-left font-medium text-gray-600">판단 결과</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {dangerRules.map((rule, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-3 text-gray-700">{rule.condition}</td>
                  <td className="px-6 py-3 text-gray-500">{rule.area}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      rule.severity === 'high'
                        ? 'bg-red-100 text-red-700'
                        : rule.severity === 'medium'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {rule.result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 시작하기 3단계 */}
      <div className="bg-white rounded-2xl border border-sv-border shadow-sm p-6">
        <h2 className="font-semibold text-gray-700 text-lg mb-4">시작하기</h2>
        <div className="grid grid-cols-3 gap-4">
          {steps.map((s) => (
            <div key={s.step} className="border border-sv-border rounded-xl p-5 hover:border-sv-green transition-colors group">
              <div className="w-9 h-9 bg-sv-green rounded-full flex items-center justify-center text-white font-bold text-lg mb-3 shadow-sm">
                {s.step}
              </div>
              <h3 className="font-semibold text-gray-800 mb-1">{s.title}</h3>
              <p className="text-gray-500 text-sm mb-3 leading-relaxed">{s.desc}</p>
              <button
                onClick={() => navigate(s.link)}
                className="text-sv-green text-sm font-medium hover:underline group-hover:text-sv-green-light transition-colors"
              >
                {s.linkLabel} →
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MetricCard({ icon, label, value, unit, color }) {
  const colorMap = {
    green: 'bg-green-50 text-sv-green border-green-100',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
    blue: 'bg-blue-50 text-blue-600 border-blue-100',
  }
  const icons = {
    roi: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
    ),
    event: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    video: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
      </svg>
    ),
  }
  return (
    <div className={`flex items-center gap-4 p-4 rounded-xl border ${colorMap[color]}`}>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorMap[color]}`}>
        {icons[icon]}
      </div>
      <div>
        <div className="text-2xl font-bold">
          {value}<span className="text-base font-normal ml-1">{unit}</span>
        </div>
        <div className="text-sm opacity-80">{label}</div>
      </div>
    </div>
  )
}
