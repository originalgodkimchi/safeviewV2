import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Monitoring from './pages/Monitoring'
import ROISettings from './pages/ROISettings'
import Events from './pages/Events'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="roi" element={<ROISettings />} />
          <Route path="events" element={<Events />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
