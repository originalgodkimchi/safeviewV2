import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-sv-bg">
      {/* 사이드바 */}
      <Sidebar />

      {/* 메인 콘텐츠 */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* 상단 헤더 */}
        <header className="bg-white border-b border-sv-border px-6 py-3 flex items-center gap-3 shadow-sm">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-sv-green rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
              </svg>
            </div>
            <div>
              <span className="font-bold text-sv-green text-lg tracking-wide">SAFE</span>
              <span className="font-bold text-gray-700 text-lg tracking-wide">VIEW</span>
            </div>
          </div>
          <div className="text-gray-400 text-sm ml-2">안전사각지대 감지 시스템</div>
        </header>

        {/* 페이지 콘텐츠 */}
        <div className="flex-1 p-6 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
