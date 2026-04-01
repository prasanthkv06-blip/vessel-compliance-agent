# Vessel Compliance Agent — Architecture v1.0.0

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TS)                     │
│  Dashboard │ Vessel Search │ Report Viewer │ Fleet Monitor   │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼──────────────────────────────────┐
│                 BACKEND (FastAPI - Python)                    │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ API Layer│  │ Orchestrator │  │  Report Engine       │   │
│  │ /vessel  │──│ (Workflow)   │──│  (HTML → PDF)        │   │
│  │ /report  │  │              │  │                      │   │
│  └──────────┘  └──────┬───────┘  └─────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │              DATA AGGREGATION LAYER                     │  │
│  │                                                         │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐  │  │
│  │  │ Identity    │ │ Ownership    │ │ Sanctions      │  │  │
│  │  │ Service     │ │ Service      │ │ Screening      │  │  │
│  │  │ (IMO/AIS)   │ │ (LLI/IHS)   │ │ (OFAC/EU/UK)   │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────┘  │  │
│  │                                                         │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐  │  │
│  │  │ Operational │ │ Flag Risk    │ │ Compliance     │  │  │
│  │  │ Risk Engine │ │ Assessor     │ │ Checker        │  │  │
│  │  │ (AIS Gaps)  │ │ (MoU/USCG)  │ │ (Class/P&I)    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    DATA LAYER                            │  │
│  │  SQLite/PostgreSQL │ Redis Cache │ File Storage (PDF)    │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ OFAC/EU/UK   │  │ AIS Providers│  │ Maritime     │
│ Sanctions    │  │ (Spire/MT)   │  │ Registries   │
│ (Public XML) │  │              │  │ (Equasis)    │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Agent Workflow (5 Phases)

### Phase 1: Identity Verification
- Input: IMO number or vessel name
- Query IMO database → confirm vessel identity
- Output: Vessel particulars (IMO, MMSI, Flag, DWT, Build year, Class)

### Phase 2: Ownership & Entity Screening
- Fetch current + historical ownership chain
- For each entity: cross-reference against OFAC SDN, EU, UK sanctions lists
- Fuzzy name matching for entity resolution
- Check jurisdiction risk (Free Zones, high-risk countries)

### Phase 3: Operational Risk Analysis
- Retrieve AIS history (configurable timeframe, default 24 months)
- **AIS Gap Detection**: Flag gaps > 24h; combine with draught change analysis
- **STS Transfer Detection**: Identify ship-to-ship ops; flag if outside designated zones
- **Port Call Risk**: Check visits to sanctioned-country ports
- **AIS Spoofing Detection**: Identify position anomalies

### Phase 4: Sanctions & Risk Aggregation
- Vessel-level: Check IMO against all sanction lists
- Cargo/Trade: Check if vessel carried sanctioned cargo (last 24 months)
- Ownership: Check if any previous owner is sanctioned
- Aggregate into risk scores: Low / Medium / High

### Phase 5: Flag Risk Assessment
- Paris MoU classification (White/Grey/Black)
- USCG Annual Targeted Flag list
- ITF Flag of Convenience designation
- IMO/ILO convention ratification status

## Data Models

### VesselIdentity
```python
class VesselIdentity:
    imo: str
    name: str
    vessel_type: str  # "Oil Products Tanker"
    flag: str
    flag_history: list[FlagRecord]
    mmsi: str
    dwt: int
    grt: int
    build_year: int
    build_country: str
    class_society: str
    sanction_status: str  # "Not sanctioned" / "Sanctioned"
```

### OwnershipRecord
```python
class OwnershipRecord:
    entity_name: str
    role: str  # registered_owner / commercial_manager / technical_manager / ism_manager
    from_date: date
    to_date: date | None  # None = current
    imo_company_number: str
    address: str
    country: str
    website: str | None
    sanction_status: str
    sanction_details: list[SanctionHit]
```

### AISGap
```python
class AISGap:
    start_time: datetime
    end_time: datetime
    duration_hours: float
    start_location: str
    end_location: str
    draught_change: float
    risk_level: str  # "Low" / "Medium" / "High"
```

### ComplianceReport
```python
class ComplianceReport:
    vessel: VesselIdentity
    ownership_history: list[OwnershipRecord]
    sanction_risks: SanctionRiskSummary
    operational_risks: OperationalRiskSummary
    flag_risks: FlagRiskSummary
    compliance_info: ComplianceInfo
    report_date: datetime
    investigation_timeframe: tuple[date, date]
    overall_risk: str  # "PASS" / "REVIEW" / "FAIL"
```

## Risk Scoring Logic

| Condition | Risk Level |
|-----------|------------|
| AIS gap > 24h + draught change > 2m in sanctioned waters | HIGH |
| AIS gap > 24h + draught change in open waters | MEDIUM |
| AIS gap > 24h, no draught change | LOW |
| STS transfer outside designated zones | HIGH |
| Port call in sanctioned country | HIGH |
| Owner in high-risk jurisdiction (no sanction match) | MEDIUM |
| Flag on Paris MoU Black list | HIGH |
| Flag on Paris MoU Grey list | MEDIUM |
| Entity fuzzy match to sanctioned name (< 90% confidence) | REVIEW |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/vessel/search | Search vessel by IMO or name |
| GET | /api/v1/vessel/{imo} | Get vessel details |
| POST | /api/v1/report/generate | Generate compliance report |
| GET | /api/v1/report/{id} | Get report by ID |
| GET | /api/v1/report/{id}/pdf | Download PDF report |
| GET | /api/v1/sanctions/check/{entity} | Check entity against sanctions |
| GET | /api/v1/fleet | List monitored fleet |
| POST | /api/v1/fleet/add | Add vessel to fleet monitoring |

## Directory Structure

```
vessel-compliance-agent/
├── CLAUDE.md
├── docs/
│   └── ARCHITECTURE.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings & API keys
│   │   ├── models/
│   │   │   ├── vessel.py        # Pydantic data models
│   │   │   ├── ownership.py
│   │   │   ├── sanctions.py
│   │   │   ├── operational.py
│   │   │   └── report.py
│   │   ├── services/
│   │   │   ├── identity.py      # Phase 1: IMO/vessel lookup
│   │   │   ├── ownership.py     # Phase 2: Ownership chain
│   │   │   ├── sanctions.py     # Phase 2+4: Sanctions screening
│   │   │   ├── ais_analysis.py  # Phase 3: AIS gaps, STS, ports
│   │   │   ├── flag_risk.py     # Phase 5: Flag assessment
│   │   │   └── compliance.py    # Phase 4: Aggregation
│   │   ├── orchestrator.py      # Workflow controller
│   │   ├── routes/
│   │   │   ├── vessel.py
│   │   │   ├── report.py
│   │   │   └── fleet.py
│   │   └── report_engine/
│   │       ├── generator.py     # HTML → PDF conversion
│   │       └── templates/
│   │           ├── report.html   # Main report template
│   │           └── styles.css    # Kpler-style CSS
│   └── tests/
│       ├── test_sanctions.py
│       ├── test_ais_analysis.py
│       └── test_report.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── VesselSearch.tsx
│   │   │   ├── ReportViewer.tsx
│   │   │   ├── RiskBadge.tsx
│   │   │   ├── OwnershipTimeline.tsx
│   │   │   └── AISGapChart.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── VesselReport.tsx
│   │   │   └── FleetMonitor.tsx
│   │   └── api/
│   │       └── client.ts
│   └── public/
├── data/
│   ├── sanctions/           # Cached OFAC/EU/UK lists
│   ├── flags/               # Paris MoU, USCG, ITF data
│   └── sample/              # Sample data for testing
└── scripts/
    ├── download_sanctions.py  # Fetch latest sanctions lists
    └── seed_data.py           # Seed test data
```

## Changelog
- **v1.0.0** (2026-04-01): Initial architecture design
