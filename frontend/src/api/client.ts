const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1'

export async function searchVessel(imo: string) {
  const res = await fetch(`${API_BASE}/vessel/${imo}`)
  if (!res.ok) throw new Error('Vessel not found')
  return res.json()
}

export async function generateReport(imo: string) {
  const res = await fetch(`${API_BASE}/report/generate?imo=${imo}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to generate report')
  return res.json()
}

export async function getReportHTML(imo: string): Promise<string> {
  const res = await fetch(`${API_BASE}/report/generate/html?imo=${imo}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to generate HTML report')
  return res.text()
}
