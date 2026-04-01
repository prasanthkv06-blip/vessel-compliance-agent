import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import VesselReport from './pages/VesselReport'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-navy-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚢</span>
            <div>
              <h1 className="text-lg font-bold tracking-wide">Vessel Compliance Agent</h1>
              <p className="text-xs text-gray-400">S&P Inspection Screening</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <a href="/" className="hover:text-blue-300 transition">Dashboard</a>
            <a href="#" className="hover:text-blue-300 transition">Fleet</a>
            <a href="#" className="hover:text-blue-300 transition">Settings</a>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/report/:imo" element={<VesselReport />} />
        </Routes>
      </main>
    </div>
  )
}
