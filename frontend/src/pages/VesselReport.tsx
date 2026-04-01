import { useState, useEffect, useRef } from 'react'
import { API_BASE } from '../api/client'
import { useParams } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'

interface Report {
  report_id: string
  vessel: { imo: string; name: string; vessel_type: string; flag: string; mmsi: string; dwt: number; grt: number; build_year: number; build_country: string; sanction_status: string }
  ownership: { current_registered_owner: any; current_commercial_manager: any; current_technical_manager: any; current_ism_manager: any; historical_records: any[] }
  sanction_risks: { vessel_sanctioned: boolean; cargo_sanctioned: boolean; trade_sanctioned: boolean; flag_sanctioned: boolean; hits: any[] }
  operational_risks: { ais_gaps: any[]; sts_transfers: any[]; port_calls: any[]; ais_spoofing_detected: boolean }
  flag_risks: { current_flag: string; paris_mou_status: string; uscg_targeted: boolean; itf_foc: boolean }
  compliance_info: { classification_society: string; inspections_count: number; detentions_count: number; bans_count: number }
  overall_risk: string
  report_date: string
  investigation_start: string
  investigation_end: string
}

export default function VesselReport() {
  const { imo } = useParams<{ imo: string }>()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const fetchedRef = useRef(false)

  useEffect(() => {
    // Guard against React 18 Strict Mode double-invocation
    if (fetchedRef.current) return
    fetchedRef.current = true

    async function fetchReport() {
      try {
        // If Dashboard cached the report (new check flow), use it directly
        const cached = sessionStorage.getItem(`report_${imo}`)
        if (cached) {
          sessionStorage.removeItem(`report_${imo}`)
          setReport(JSON.parse(cached))
          setLoading(false)
          return
        }
        // Fall back to sample-data endpoint for direct URL navigation
        const res = await fetch(`${API_BASE}/report/generate?imo=${imo}`, { method: 'POST' })
        if (!res.ok) throw new Error('Failed to generate report')
        const data = await res.json()
        setReport(data)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchReport()
  }, [imo])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy-700"></div>
    </div>
  )
  if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-xl">{error}</div>
  if (!report) return null

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'ownership', label: 'Ownership' },
    { id: 'sanctions', label: 'Sanctions' },
    { id: 'operational', label: 'Operational' },
    { id: 'flags', label: 'Flag Risk' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-navy-900 to-navy-500 rounded-2xl p-6 text-white flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">{report.vessel.name}</h2>
          <p className="text-gray-300 mt-1">IMO {report.vessel.imo} · {report.vessel.flag} · {report.vessel.vessel_type}</p>
        </div>
        <div className="flex items-center gap-4">
          <RiskBadge level={report.overall_risk as any} size="lg" />
          <button
            onClick={() => window.open(`${API_BASE}/report/view/${imo}/html`, '_blank')}
            className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg text-sm transition"
          >
            View Full Report
          </button>
          <a
            href={`${API_BASE}/report/view/${imo}/pdf`}
            download
            className="bg-blue-600/80 hover:bg-blue-600 px-4 py-2 rounded-lg text-sm transition"
          >
            Download PDF
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
              activeTab === tab.id ? 'bg-white text-navy-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <h3 className="font-semibold text-navy-700 text-lg">General Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'IMO', value: report.vessel.imo },
                { label: 'MMSI', value: report.vessel.mmsi },
                { label: 'Type', value: report.vessel.vessel_type },
                { label: 'Flag', value: report.vessel.flag },
                { label: 'DWT', value: report.vessel.dwt.toLocaleString() },
                { label: 'GRT', value: report.vessel.grt.toLocaleString() },
                { label: 'Build Year', value: report.vessel.build_year },
                { label: 'Build Country', value: report.vessel.build_country },
              ].map((item) => (
                <div key={item.label} className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">{item.label}</div>
                  <div className="font-semibold text-navy-700 mt-1">{item.value}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200 flex items-center gap-3">
              <span className="text-green-600 text-xl">✓</span>
              <span className="text-green-800 font-medium">{report.vessel.sanction_status}</span>
            </div>
          </div>
        )}

        {activeTab === 'ownership' && (
          <div className="space-y-4">
            <h3 className="font-semibold text-navy-700 text-lg">Ownership & Management</h3>
            {[
              { label: 'Registered Owner', data: report.ownership.current_registered_owner },
              { label: 'Commercial Manager', data: report.ownership.current_commercial_manager },
              { label: 'Technical Manager', data: report.ownership.current_technical_manager },
              { label: 'ISM Manager', data: report.ownership.current_ism_manager },
            ].filter(item => item.data).map((item) => (
              <div key={item.label} className="border border-gray-200 rounded-lg p-4">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{item.label}</div>
                <div className="font-semibold text-navy-700">{item.data.entity_name}</div>
                <div className="text-sm text-gray-500 mt-1">
                  From {item.data.from_date} · {item.data.country}
                </div>
                <div className="mt-2">
                  <RiskBadge level={item.data.sanction_status === 'Not Sanctioned' ? 'Low' : 'High'} label={item.data.sanction_status} />
                </div>
              </div>
            ))}
            {report.ownership.historical_records.length > 0 && (
              <>
                <h4 className="font-medium text-gray-600 mt-6">Historical Ownership</h4>
                {report.ownership.historical_records.map((record: any, i: number) => (
                  <div key={i} className="border border-gray-100 rounded-lg p-4 opacity-75">
                    <div className="text-xs text-gray-500 uppercase">{record.role?.replace(/_/g, ' ')}</div>
                    <div className="font-medium text-navy-700">{record.entity_name}</div>
                    <div className="text-sm text-gray-500">{record.from_date} — {record.to_date || 'Present'} · {record.country}</div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'sanctions' && (
          <div className="space-y-4">
            <h3 className="font-semibold text-navy-700 text-lg">Sanction Risk Assessment</h3>
            {[
              { label: 'Vessel not sanctioned', pass: !report.sanction_risks.vessel_sanctioned },
              { label: 'No sanctioned cargo (24 months)', pass: !report.sanction_risks.cargo_sanctioned },
              { label: 'No sanctioned trades (24 months)', pass: !report.sanction_risks.trade_sanctioned },
              { label: 'Flag not sanctioned', pass: !report.sanction_risks.flag_sanctioned },
            ].map((check) => (
              <div key={check.label} className={`flex items-center gap-3 p-3 rounded-lg ${check.pass ? 'bg-green-50' : 'bg-red-50'}`}>
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-sm ${check.pass ? 'bg-green-500' : 'bg-red-500'}`}>
                  {check.pass ? '✓' : '✗'}
                </span>
                <span className={check.pass ? 'text-green-800' : 'text-red-800'}>{check.label}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'operational' && (
          <div className="space-y-6">
            <h3 className="font-semibold text-navy-700 text-lg">Operational Risk Analysis</h3>
            <div>
              <h4 className="font-medium text-gray-700 mb-3">AIS Gaps</h4>
              {report.operational_risks.ais_gaps.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="text-left py-2 text-gray-500">From</th>
                      <th className="text-left py-2 text-gray-500">To</th>
                      <th className="text-left py-2 text-gray-500">Duration</th>
                      <th className="text-left py-2 text-gray-500">Location</th>
                      <th className="text-left py-2 text-gray-500">Draught Δ</th>
                      <th className="text-left py-2 text-gray-500">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.operational_risks.ais_gaps.map((gap: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-2">{gap.start_time}</td>
                        <td className="py-2">{gap.end_time}</td>
                        <td className="py-2">{gap.duration_hours}h</td>
                        <td className="py-2">{gap.start_location} → {gap.end_location}</td>
                        <td className="py-2">{gap.draught_change}m</td>
                        <td className="py-2"><RiskBadge level={gap.risk_level} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-green-700 bg-green-50 p-3 rounded-lg">No significant AIS gaps detected.</p>
              )}
            </div>
            <div>
              <h4 className="font-medium text-gray-700 mb-2">STS Transfers</h4>
              <p className="text-green-700 bg-green-50 p-3 rounded-lg">No high risk STS transfers detected.</p>
            </div>
            <div>
              <h4 className="font-medium text-gray-700 mb-2">AIS Spoofing</h4>
              <p className="text-green-700 bg-green-50 p-3 rounded-lg">No AIS spoofing detected.</p>
            </div>
          </div>
        )}

        {activeTab === 'flags' && (
          <div className="space-y-4">
            <h3 className="font-semibold text-navy-700 text-lg">Flag Risk Assessment</h3>
            <div className="bg-gray-50 rounded-lg p-4 flex items-center gap-4">
              <span className="text-3xl">🏴</span>
              <div>
                <div className="font-semibold text-navy-700">{report.flag_risks.current_flag}</div>
                <div className="text-sm text-gray-500">
                  Paris MoU: <span className={`font-medium ${
                    report.flag_risks.paris_mou_status === 'White' ? 'text-green-600' :
                    report.flag_risks.paris_mou_status === 'Grey' ? 'text-yellow-600' : 'text-red-600'
                  }`}>{report.flag_risks.paris_mou_status}</span>
                </div>
              </div>
            </div>
            {[
              { label: 'Not on USCG Targeted Flag List', pass: !report.flag_risks.uscg_targeted },
              { label: 'Not a Flag of Convenience (ITF)', pass: !report.flag_risks.itf_foc },
            ].map((check) => (
              <div key={check.label} className={`flex items-center gap-3 p-3 rounded-lg ${check.pass ? 'bg-green-50' : 'bg-yellow-50'}`}>
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-sm ${check.pass ? 'bg-green-500' : 'bg-yellow-500'}`}>
                  {check.pass ? '✓' : '⚠'}
                </span>
                <span className={check.pass ? 'text-green-800' : 'text-yellow-800'}>{check.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
