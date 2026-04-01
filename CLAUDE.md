# Vessel Compliance Automation Agent

## Project Overview
An automated vessel compliance screening agent for Sale & Purchase (S&P) inspections. Ingests a vessel's IMO number and outputs a standardized compliance report (PDF/HTML) verifying the vessel, its owners, and operational history are "clean" from sanctions and high-risk activities.

## Version History

### v1.2.0 — Phase 1 & 2 Enhanced Compliance Checks (2026-04-01) ✅ CURRENT

**10 new compliance checks added (all free / public data sources, no new API keys required):**

**Phase 1 — High Priority:**
- **Multi-List Sanctions Screening** (`services/sanctions_engine.py`): OFAC SDN XML (downloaded, cached 24h, IMO + fuzzy name match) + OpenSanctions free search API (aggregates EU, UK HM Treasury, UN Security Council, 200+ lists). 4-list grid displayed on report.
- **PSC Deep Analysis** (`services/psc_analyzer.py`): Equasis `ShipInspection` page scraping — detention rate %, deficiency category breakdown (8 categories), recent inspection table, trend detection (improving/stable/deteriorating), USCG sub-count via PSIX public database.
- **Certificate Matrix** (`services/certificate_service.py`): 12 required certificates (+ tanker-specific extras) with Valid/Expiring Soon/Expired/Not Verified status from Equasis `ShipCertificate` page. Expiry warning at <90 days.
- **Enhanced Flag Risk Scoring** (`services/flag_risk.py`): Added FATF Grey/Black List (2024), USCG Annual Targeted Flag List (2024), composite risk score 0–100, flag-hopping detection (≥3 changes in 3 years).
- **Ownership Velocity & Anomaly Detection** (`services/ownership_analyzer.py`): Counts ownership changes, flag changes, name changes in last 3 years. Flags rapid turnover, flag hopping, identity evasion patterns.

**Phase 2 — Medium Priority:**
- **USCG PSIX Record** (integrated into `psc_analyzer.py`): Scrapes USCG public PSC database for US-specific detention history.
- **CII Grade Estimate + EU ETS** (`services/cii_calculator.py`): IMO MEPC.337(76) formula-based estimate (A–E) from vessel age, type, DWT. EU ETS applicability flagged for vessels >5,000 GT. Sulphur/ECA note included.
- **Casualty & Incident History** (`services/casualty_service.py`): Equasis `ShipCasualty` page scraping — collision, grounding, fire, structural incidents with date/location/severity.
- **Sister Vessel / Owner Fleet Risk** (`services/ownership_analyzer.py`): Owner entity noted, fleet risk indicator; full fleet lookup requires Equasis company page (future enhancement).
- **Name/Flag Change Anomaly Detection** (combined in `ownership_analyzer.py`): Equasis `ShipHistory` name and flag history parsed; multiple renames or rapid flag changes flagged as identity risk.

**Equasis scraper extended** (`services/equasis.py`):
- Added `fetch_inspections()`, `fetch_certificates()`, `fetch_casualties()` — scrape 3 new Equasis restricted pages
- Added `_parse_name_flag_history()` — extracts name history and flag history from ShipHistory page
- `lookup_vessel()` now returns `name_history` and `flag_history` alongside ownership

**New data models** (`models/report.py`): `Certificate`, `CertificateMatrix`, `PSCDeficiency`, `PSCInspectionDetail`, `PSCAnalysis`, `CIIRating`, `CasualtyEvent`, `CasualtyHistory`, `SisterVessel`, `SisterVesselRisk`, `OwnershipVelocity`, `SanctionsMultiListResult`

**Report extended to 12+ pages**:
- Page 4 (Sanctions) — enhanced with 4-list OFAC/EU/UK/UN badge grid + multi-list hit table
- Page 7 (Flag Risk) — enhanced with FATF badge, composite risk score bar
- **Page 8** (NEW) — Certificate Matrix
- **Page 9** (NEW) — PSC Deep Analysis with KPI bar + deficiency chart
- **Page 10** (NEW) — CII Grade + EU ETS + Sulphur/ECA compliance
- **Page 11** (NEW) — Casualty & Incident History
- **Page 12** (NEW) — Ownership Velocity & Sister Vessel Risk

**Orchestrator** (`orchestrator.py`): All new services run concurrently via `asyncio.gather`. `_run_enhanced_checks()` helper coordinates 10 checks. Risk aggregation updated to include PSC, casualty, and ownership velocity in overall risk score.

---

### v1.1.0 — Auto-Lookup, PDF Export & Vessel Photo (2026-04-01)
**Features added:**
- **IMO Auto-Lookup**: Enter a 7-digit IMO → all vessel details auto-populated via Equasis scraper (600ms debounce). IMO is primary key; vessel name is compared using fuzzy match (difflib SequenceMatcher ≥ 0.85 ratio). Mismatch shows amber warning banner.
- **Equasis Integration** (`backend/app/services/equasis.py`): Session-based login via `authen/HomePage`, vessel info from `restricted/ShipInfo?P_IMO=`, ownership history from `restricted/ShipHistory?P_IMO=`. Handles `\xa0` non-breaking spaces, vessel name parsed from `h4` tag.
- **Credentials configured** in `backend/.env`: `EQUASIS_USERNAME` / `EQUASIS_PASSWORD`
- **A4 PDF Report** (`WeasyPrint`): `@page { size: A4; margin: 18mm 20mm; }`. Endpoints return `FileResponse` with `application/pdf` MIME type and auto-named file (`VCR-{IMO}-{NAME}.pdf`).
- **Vessel Photo on Cover Page** (`backend/app/services/vessel_photo.py`): Fetches real JPEG from MarineTraffic CDN (`photos.marinetraffic.com/ais/showphoto.aspx?imo={imo}`) — no API key needed. Base64-encoded as data URI, embedded as a full-width photo strip with dark gradient overlay on the cover page.
- **Ownership Card Fix**: Replaced `position: absolute` badge with flexbox header row — role label + "NOT SANCTIONED" badge no longer overlap on long role names.
- **Download PDF button** added to frontend `VesselReport.tsx`.

**Key files added/modified:**
- `backend/app/services/equasis.py` (NEW)
- `backend/app/services/vessel_photo.py` (NEW)
- `backend/app/models/report.py` — added `vessel_photo: Optional[str]`
- `backend/app/orchestrator.py` — auto-lookup + photo fetch integrated
- `backend/app/routes/vessel.py` — `GET /api/v1/vessel/lookup/{imo}` endpoint
- `backend/app/routes/report.py` — PDF `FileResponse` endpoints
- `backend/app/report_engine/templates/report.html` — ownership card flex layout + cover photo strip
- `frontend/src/components/VesselSearch.tsx` — debounced auto-lookup, pre-fill, name mismatch warning
- `frontend/src/pages/VesselReport.tsx` — Download PDF button
- `backend/.env` — Equasis credentials
- `backend/requirements.txt` — added `beautifulsoup4==4.12.3`

### v1.0.0 — Initial project scaffold and architecture (2026-04-01)

## Team Roles
- **Project Head**: Oversees entire project delivery, ensures objectives are met
- **Research Analyst**: Reviews requirements, prepares project outline, maps data sources
- **Frontend UI**: Designs and builds the React-based dashboard
- **Backend Developer**: Core logic, API integrations, data aggregation, report engine
- **QA/QC Tester**: Tests every component, validates against Kpler report standard

## Tech Stack
- **Frontend**: React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: Python (FastAPI) — data aggregation, sanctions screening, AIS analysis
- **Report Engine**: HTML/CSS templates → PDF via WeasyPrint/Playwright
- **Database**: SQLite (dev) / PostgreSQL (prod) for caching vessel data
- **API Layer**: REST endpoints for frontend-backend communication

## Report Sections (Based on Kpler Report Structure)
1. Cover Page — Vessel photo strip (MarineTraffic CDN), vessel name, IMO, report date
2. Summary — Sanction status, investigation timeframe
3. General Info — IMO, Class, Build country, MMSI, DWT, Flag, GRT
4. Ownership Structure — Current + historical (Registered Owner, Commercial Manager, Technical Manager, ISM Manager)
5. Sanction Risks — Vessel, cargo, trade, entity, flag sanctions
6. Compliance — Classification society, P&I club, inspections, detentions, bans
7. Operational Risks — AIS gaps, STS transfers, Dark STS, port call risks, AIS spoofing
8. Flag Risks — Paris MoU, USCG targeted flag, ITF FOC, IMO/ILO conventions
9. Appendix — Detailed AIS gap timeline, flag history

## Data Sources
### Free/Public
- OFAC SDN List (XML/CSV)
- EU Consolidated Sanctions List (XML)
- UK Sanctions List (CSV)
- Paris MoU White/Grey/Black lists
- ITF Flag of Convenience list
- Equasis (free registration required)
- UN Sanctions Lists

### Commercial (API keys required)
- **AIS**: Spire Maritime, MarineTraffic, VesselFinder
- **Ownership**: Lloyd's List Intelligence (LLI), IHS Markit / S&P Global
- **Cargo/Trade**: Kpler API, Vortexa
- **Sanctions Screening**: ComplyAdvantage, World-Check, Dow Jones
- **Corporate Registry**: OpenCorporates

## Key Commands
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Generate report
python -m backend.report_generator --imo 9662693
```

## Architecture
See `docs/ARCHITECTURE.md` for full system design.

## Coding Standards
- Python: PEP 8, type hints, async where possible
- TypeScript: strict mode, ESLint + Prettier
- All API responses follow consistent JSON schema
- Error handling at system boundaries only
- No speculative abstractions
