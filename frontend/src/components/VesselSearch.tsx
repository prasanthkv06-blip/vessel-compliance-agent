import { useState, useEffect, useRef } from 'react'
import { API_BASE } from '../api/client'

export interface OwnerInput {
  entity_name: string
  role: string
  country: string
  from_date: string
  to_date: string
  is_historical: boolean
}

export interface VesselCheckRequest {
  imo: string
  vessel_name: string
  vessel_type: string
  flag: string
  mmsi: string
  dwt: string
  grt: string
  build_year: string
  build_country: string
  class_society: string
  owners: OwnerInput[]
  created_by: string
}

interface LookupResult {
  imo: string
  found: boolean
  source: 'equasis' | 'sample'
  vessel: {
    name?: string
    vessel_type?: string
    flag?: string
    mmsi?: string
    dwt?: number
    grt?: number
    build_year?: number
    build_country?: string
    class_society?: string
  }
  ownership: OwnerInput[]
  name_found: string
  name_match: boolean | null
}

interface Props {
  onSubmit: (req: VesselCheckRequest) => void
  loading?: boolean
}

const ROLES = [
  { value: 'registered_owner',   label: 'Registered Owner' },
  { value: 'commercial_manager', label: 'Commercial Manager' },
  { value: 'technical_manager',  label: 'Technical Manager' },
  { value: 'ism_manager',        label: 'ISM Manager' },
  { value: 'operator',           label: 'Operator' },
  { value: 'beneficial_owner',   label: 'Beneficial Owner' },
]

const emptyOwner = (): OwnerInput => ({
  entity_name: '', role: 'registered_owner', country: '',
  from_date: '', to_date: '', is_historical: false,
})

const emptyForm = (): VesselCheckRequest => ({
  imo: '', vessel_name: '', vessel_type: '', flag: '',
  mmsi: '', dwt: '', grt: '', build_year: '', build_country: '',
  class_society: '', owners: [emptyOwner()], created_by: '',
})

export default function VesselSearch({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<VesselCheckRequest>(emptyForm())
  const [detailsExpanded, setDetailsExpanded] = useState(false)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupResult, setLookupResult] = useState<LookupResult | null>(null)
  const [lookupError, setLookupError] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const set = (field: keyof VesselCheckRequest, value: string) =>
    setForm(f => ({ ...f, [field]: value }))

  const setOwner = (i: number, field: keyof OwnerInput, value: string | boolean) =>
    setForm(f => {
      const owners = [...f.owners]
      owners[i] = { ...owners[i], [field]: value }
      return { ...f, owners }
    })

  const addOwner = () =>
    setForm(f => ({ ...f, owners: [...f.owners, emptyOwner()] }))

  const removeOwner = (i: number) =>
    setForm(f => ({ ...f, owners: f.owners.filter((_, idx) => idx !== i) }))

  // Auto-lookup when IMO reaches 7 digits
  useEffect(() => {
    const imo = form.imo
    if (imo.length !== 7) {
      setLookupResult(null)
      setLookupError('')
      return
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setLookupLoading(true)
      setLookupError('')
      try {
        const params = new URLSearchParams({ ...(form.vessel_name ? { vessel_name: form.vessel_name } : {}) })
        const res = await fetch(`${API_BASE}/vessel/lookup/${imo}?${params}`)
        if (!res.ok) {
          const err = await res.json()
          setLookupError(err.detail || 'Vessel not found in registry. Please enter details manually.')
          setLookupResult(null)
          return
        }
        const data: LookupResult = await res.json()
        setLookupResult(data)

        // Pre-fill form with fetched data (user values take precedence)
        const v = data.vessel
        setForm(f => ({
          ...f,
          vessel_name: f.vessel_name || v.name || '',
          vessel_type: f.vessel_type || v.vessel_type || '',
          flag: f.flag || v.flag || '',
          mmsi: f.mmsi || (v.mmsi ? String(v.mmsi) : ''),
          dwt: f.dwt || (v.dwt ? String(v.dwt) : ''),
          grt: f.grt || (v.grt ? String(v.grt) : ''),
          build_year: f.build_year || (v.build_year ? String(v.build_year) : ''),
          build_country: f.build_country || v.build_country || '',
          class_society: f.class_society || v.class_society || '',
          // Pre-fill ownership only if user hasn't entered any yet
          owners: f.owners.every(o => !o.entity_name.trim()) && data.ownership.length > 0
            ? data.ownership
            : f.owners,
        }))
      } catch {
        setLookupError('Could not reach registry. Please enter details manually.')
      } finally {
        setLookupLoading(false)
      }
    }, 600)

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [form.imo]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.imo.trim()) return
    onSubmit(form)
  }

  const inputCls = "w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
  const labelCls = "block text-xs text-gray-400 mb-1 font-medium"

  const sourceLabel = lookupResult?.source === 'equasis'
    ? { text: 'Equasis', color: 'bg-green-500/20 text-green-300 border-green-500/30' }
    : lookupResult?.source === 'sample'
    ? { text: 'Demo Data', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30' }
    : null

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* ── Row 1: IMO + Vessel Name ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* IMO */}
        <div className="w-full sm:w-48">
          <label className={labelCls}>IMO Number <span className="text-red-400">*</span></label>
          <div className="relative">
            <input
              type="text"
              value={form.imo}
              onChange={e => setForm(f => ({
                ...emptyForm(),
                imo: e.target.value.replace(/\D/g, '').slice(0, 7),
                created_by: f.created_by,
              }))}
              placeholder="e.g. 9759252"
              required
              maxLength={7}
              className={inputCls}
            />
            {lookupLoading && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2">
                <svg className="animate-spin h-4 w-4 text-blue-400" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
              </div>
            )}
            {lookupResult && !lookupLoading && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2 text-green-400 text-sm">✓</div>
            )}
          </div>
        </div>

        {/* Vessel Name */}
        <div className="flex-1">
          <label className={labelCls}>
            Vessel Name
            {lookupResult && (
              <span className="ml-2 text-gray-500 font-normal">(auto-filled)</span>
            )}
          </label>
          <input
            type="text"
            value={form.vessel_name}
            onChange={e => set('vessel_name', e.target.value)}
            placeholder="e.g. MARVEL PELICAN"
            className={inputCls}
          />
        </div>

        {/* Flag (shown by default) */}
        <div className="w-full sm:w-44">
          <label className={labelCls}>
            Flag State
            {lookupResult && <span className="ml-2 text-gray-500 font-normal">(auto-filled)</span>}
          </label>
          <input
            type="text"
            value={form.flag}
            onChange={e => set('flag', e.target.value.toUpperCase())}
            placeholder="e.g. PANAMA"
            className={inputCls}
          />
        </div>

        <div className="self-end">
          <button
            type="button"
            onClick={() => setDetailsExpanded(!detailsExpanded)}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-gray-300 transition whitespace-nowrap"
          >
            {detailsExpanded ? 'Less ▲' : 'More details ▼'}
          </button>
        </div>
      </div>

      {/* ── Lookup status messages ── */}
      {lookupResult && !lookupLoading && (
        <div className="flex items-center gap-3 flex-wrap">
          {sourceLabel && (
            <span className={`text-xs px-2 py-1 rounded border font-medium ${sourceLabel.color}`}>
              Source: {sourceLabel.text}
            </span>
          )}
          <span className="text-xs text-gray-400">
            Registry name: <span className="text-white font-medium">{lookupResult.name_found}</span>
          </span>
          {lookupResult.name_match === false && (
            <span className="flex items-center gap-1 text-xs bg-amber-500/20 border border-amber-500/30 text-amber-300 px-2 py-1 rounded">
              ⚠ Name mismatch — entered "{form.vessel_name}" but registry shows "{lookupResult.name_found}"
            </span>
          )}
          {lookupResult.name_match === true && form.vessel_name && (
            <span className="text-xs text-green-400">✓ Vessel name verified</span>
          )}
        </div>
      )}

      {lookupError && (
        <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          ⚠ {lookupError}
        </div>
      )}

      {/* ── Vessel Details (expandable) ── */}
      {detailsExpanded && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
          <div>
            <label className={labelCls}>Vessel Type</label>
            <input type="text" value={form.vessel_type} onChange={e => set('vessel_type', e.target.value)}
              placeholder="Oil Products Tanker" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>MMSI</label>
            <input type="text" value={form.mmsi} onChange={e => set('mmsi', e.target.value)}
              placeholder="403738380" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>DWT</label>
            <input type="number" value={form.dwt} onChange={e => set('dwt', e.target.value)}
              placeholder="3591" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>GRT</label>
            <input type="number" value={form.grt} onChange={e => set('grt', e.target.value)}
              placeholder="2239" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Build Year</label>
            <input type="number" value={form.build_year} onChange={e => set('build_year', e.target.value)}
              placeholder="2014" min={1950} max={new Date().getFullYear()} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Build Country</label>
            <input type="text" value={form.build_country} onChange={e => set('build_country', e.target.value)}
              placeholder="China" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Class Society</label>
            <input type="text" value={form.class_society} onChange={e => set('class_society', e.target.value)}
              placeholder="Bureau Veritas" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Analyst Name</label>
            <input type="text" value={form.created_by} onChange={e => set('created_by', e.target.value)}
              placeholder="Your name / firm" className={inputCls} />
          </div>
        </div>
      )}

      {/* ── Owner / Operator Section ── */}
      <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-semibold text-white">Owner &amp; Operator Details</span>
            {lookupResult && lookupResult.ownership.length > 0 && (
              <span className="text-xs text-gray-400 ml-2">— auto-fetched from {lookupResult.source === 'equasis' ? 'Equasis' : 'registry'}</span>
            )}
            {(!lookupResult || lookupResult.ownership.length === 0) && (
              <span className="text-xs text-gray-400 ml-2">— enter present owner + historical if known</span>
            )}
          </div>
          <button
            type="button"
            onClick={addOwner}
            className="text-xs px-3 py-1.5 bg-blue-500/30 hover:bg-blue-500/50 text-blue-200 rounded-lg transition font-medium"
          >
            + Add Entity
          </button>
        </div>

        {form.owners.map((owner, i) => (
          <div key={i} className={`rounded-lg p-3 border space-y-2 ${owner.is_historical ? 'border-white/10 bg-white/5' : 'border-blue-400/20 bg-blue-900/20'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded ${owner.is_historical ? 'bg-gray-600/40 text-gray-300' : 'bg-blue-500/30 text-blue-200'}`}>
                {owner.is_historical ? 'Historical' : 'Current'}
              </span>
              <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer ml-auto">
                <input
                  type="checkbox"
                  checked={owner.is_historical}
                  onChange={e => setOwner(i, 'is_historical', e.target.checked)}
                  className="rounded"
                />
                Mark as historical
              </label>
              {form.owners.length > 1 && (
                <button type="button" onClick={() => removeOwner(i)}
                  className="text-red-400 hover:text-red-300 text-lg leading-none ml-1">×</button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="sm:col-span-2">
                <label className={labelCls}>Entity Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={owner.entity_name}
                  onChange={e => setOwner(i, 'entity_name', e.target.value)}
                  placeholder="e.g. ALIYAH BUNKERING CO FZE"
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>Role</label>
                <select
                  value={owner.role}
                  onChange={e => setOwner(i, 'role', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-900 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
                >
                  {ROLES.map(r => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div>
                <label className={labelCls}>Country</label>
                <input
                  type="text"
                  value={owner.country}
                  onChange={e => setOwner(i, 'country', e.target.value.toUpperCase())}
                  placeholder="UAE"
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>From Date</label>
                <input
                  type="date"
                  value={owner.from_date}
                  onChange={e => setOwner(i, 'from_date', e.target.value)}
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>To Date <span className="font-normal opacity-60">(if historical)</span></label>
                <input
                  type="date"
                  value={owner.to_date}
                  onChange={e => setOwner(i, 'to_date', e.target.value)}
                  className={inputCls}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Analyst Name (outside expander for convenience) ── */}
      {!detailsExpanded && (
        <div className="w-full sm:w-64">
          <label className={labelCls}>Analyst / Firm Name</label>
          <input
            type="text"
            value={form.created_by}
            onChange={e => set('created_by', e.target.value)}
            placeholder="Your name / firm"
            className={inputCls}
          />
        </div>
      )}

      {/* ── Submit ── */}
      <button
        type="submit"
        disabled={!form.imo.trim() || loading || lookupLoading}
        className="w-full sm:w-auto px-10 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-semibold transition shadow-lg text-base"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Running compliance check...
          </span>
        ) : 'Run Compliance Check'}
      </button>
    </form>
  )
}
