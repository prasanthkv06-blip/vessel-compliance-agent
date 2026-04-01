import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import VesselSearch, { VesselCheckRequest } from '../components/VesselSearch'
import RiskBadge from '../components/RiskBadge'

interface RecentReport {
  imo: string
  name: string
  flag: string
  risk: 'Low' | 'Medium' | 'High'
  date: string
}

const recentReports: RecentReport[] = [
  { imo: '9662693', name: 'TWENTYSEVEN', flag: 'SAUDI ARABIA', risk: 'Medium', date: '2026-02-05' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (req: VesselCheckRequest) => {
    setLoading(true)
    setError('')

    // Build the API request body
    const body = {
      imo: req.imo,
      vessel_name: req.vessel_name || undefined,
      vessel_type: req.vessel_type || undefined,
      flag: req.flag || undefined,
      dwt: req.dwt ? parseInt(req.dwt) : undefined,
      build_year: req.build_year ? parseInt(req.build_year) : undefined,
      build_country: req.build_country || undefined,
      class_society: req.class_society || undefined,
      owners: req.owners.filter((o) => o.entity_name.trim()).map((o) => ({
        entity_name: o.entity_name,
        role: o.role,
        country: o.country || undefined,
        from_date: o.from_date || undefined,
        to_date: o.to_date || undefined,
        is_historical: o.is_historical,
      })),
      grt: req.grt ? parseInt(req.grt) : undefined,
      mmsi: req.mmsi || undefined,
      created_by: req.created_by || undefined,
    }

    try {
      const res = await fetch('/api/v1/report/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to generate report')
      }
      const report = await res.json()
      // Cache the report so VesselReport can display without a second API call
      sessionStorage.setItem(`report_${req.imo}`, JSON.stringify(report))
      navigate(`/report/${req.imo}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero Search */}
      <div className="bg-gradient-to-r from-navy-900 via-navy-500 to-navy-700 rounded-2xl p-8 text-white">
        <h2 className="text-2xl font-bold mb-2">Vessel Compliance Check</h2>
        <p className="text-gray-300 mb-6">
          Enter the vessel's IMO number and details to run a full compliance screening against
          OFAC, EU, and UK sanctions lists.
        </p>
        <VesselSearch onSubmit={handleSubmit} loading={loading} />
        {error && (
          <div className="mt-4 p-3 bg-red-500/20 border border-red-400/30 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Reports Generated', value: '1', icon: '📋' },
          { label: 'Vessels Monitored', value: '1', icon: '🚢' },
          { label: 'Sanctions Lists Active', value: '2', icon: '🔍' },
          { label: 'High Risk Alerts', value: '0', icon: '🚨' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{stat.icon}</span>
              <div>
                <div className="text-2xl font-bold text-navy-700">{stat.value}</div>
                <div className="text-sm text-gray-500">{stat.label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Reports */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-5 border-b border-gray-100">
          <h3 className="font-semibold text-navy-700">Recent Reports</h3>
        </div>
        <div className="divide-y divide-gray-50">
          {recentReports.map((r) => (
            <div
              key={r.imo}
              className="p-4 flex items-center justify-between hover:bg-gray-50 cursor-pointer transition"
              onClick={() => navigate(`/report/${r.imo}`)}
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-navy-50 flex items-center justify-center text-navy-700 font-bold text-sm">
                  {r.name[0]}
                </div>
                <div>
                  <div className="font-medium text-navy-700">{r.name}</div>
                  <div className="text-sm text-gray-500">IMO {r.imo} · {r.flag}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <RiskBadge level={r.risk} />
                <span className="text-sm text-gray-400">{r.date}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
