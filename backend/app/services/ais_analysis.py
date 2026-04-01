"""Phase 3: AIS Gap Analysis & Operational Risk Service"""
from datetime import datetime, date
from typing import Optional
from ..models.operational import AISGap, STSTransfer, PortCall, OperationalRiskSummary
from ..models.vessel import RiskLevel
from ..config import settings


# Countries under comprehensive sanctions
SANCTIONED_COUNTRIES = {
    "IRAN", "NORTH KOREA", "SYRIA", "CUBA", "CRIMEA",
    "DONETSK", "LUHANSK", "RUSSIA",  # Sectoral
}

# High-risk STS zones (approximate lat/lon bounding boxes)
HIGH_RISK_STS_ZONES = [
    {"name": "Gulf of Oman", "lat_min": 24.0, "lat_max": 27.0, "lon_min": 56.0, "lon_max": 60.0},
    {"name": "Strait of Hormuz", "lat_min": 25.5, "lat_max": 27.0, "lon_min": 55.0, "lon_max": 57.0},
    {"name": "East of Oman", "lat_min": 22.0, "lat_max": 26.0, "lon_min": 58.0, "lon_max": 62.0},
]


class AISAnalysisService:
    """Analyzes vessel AIS data for operational risks."""

    # Sample AIS gap for TWENTYSEVEN
    SAMPLE_GAPS = {
        "9662693": [
            AISGap(
                start_time=datetime(2025, 1, 15, 17, 29),
                end_time=datetime(2025, 1, 17, 3, 40),
                duration_hours=34.2,
                start_location="Vietnam",
                end_location="Vietnam",
                draught_change=0.1,
                risk_level=RiskLevel.MEDIUM,
            ),
        ],
    }

    async def analyze(self, imo: str, start_date: date, end_date: date) -> OperationalRiskSummary:
        """Run full operational risk analysis for a vessel."""
        summary = OperationalRiskSummary()

        # Load sample data or query AIS provider
        if imo in self.SAMPLE_GAPS:
            summary.ais_gaps = self.SAMPLE_GAPS[imo]
        else:
            # In production: query Spire/MarineTraffic AIS API
            raw_ais = await self._fetch_ais_data(imo, start_date, end_date)
            summary.ais_gaps = self._detect_gaps(raw_ais)
            summary.sts_transfers = self._detect_sts(raw_ais)
            summary.port_calls = self._analyze_port_calls(raw_ais)

        # Determine highest risk
        risks = [g.risk_level for g in summary.ais_gaps]
        risks += [s.risk_level for s in summary.sts_transfers]
        risks += [p.risk_level for p in summary.port_calls if p.is_sanctioned_country]

        if RiskLevel.HIGH in risks:
            summary.highest_risk = RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risks:
            summary.highest_risk = RiskLevel.MEDIUM
        elif risks:
            summary.highest_risk = RiskLevel.LOW

        return summary

    async def _fetch_ais_data(self, imo: str, start_date: date, end_date: date) -> list[dict]:
        """Fetch raw AIS position data from provider API."""
        # Placeholder -- implement with actual AIS API
        return []

    def _detect_gaps(self, ais_positions: list[dict]) -> list[AISGap]:
        """Detect AIS signal gaps > 24h and assess risk."""
        gaps = []
        for i in range(1, len(ais_positions)):
            prev = ais_positions[i - 1]
            curr = ais_positions[i]

            prev_time = datetime.fromisoformat(prev["timestamp"])
            curr_time = datetime.fromisoformat(curr["timestamp"])
            duration = (curr_time - prev_time).total_seconds() / 3600

            if duration >= 24:
                draught_change = abs(
                    float(curr.get("draught", 0)) - float(prev.get("draught", 0))
                )
                risk = self._assess_gap_risk(
                    duration, draught_change,
                    prev.get("location", ""), curr.get("location", ""),
                    prev.get("lat"), prev.get("lon"),
                )
                gaps.append(AISGap(
                    start_time=prev_time,
                    end_time=curr_time,
                    duration_hours=round(duration, 1),
                    start_location=prev.get("location", "Unknown"),
                    end_location=curr.get("location", "Unknown"),
                    draught_change=draught_change,
                    risk_level=risk,
                ))
        return gaps

    def _assess_gap_risk(self, duration_hours: float, draught_change: float,
                         start_loc: str, end_loc: str,
                         lat: Optional[float] = None, lon: Optional[float] = None) -> RiskLevel:
        """Determine risk level of an AIS gap."""
        # High risk: gap in sanctioned waters + draught change
        if lat and lon:
            for zone in HIGH_RISK_STS_ZONES:
                if (zone["lat_min"] <= lat <= zone["lat_max"] and
                    zone["lon_min"] <= lon <= zone["lon_max"]):
                    if draught_change > 0.5:
                        return RiskLevel.HIGH

        # High risk: draught change > 2m anywhere
        if draught_change > 2.0:
            return RiskLevel.HIGH

        # Medium risk: gap with minor draught change
        if draught_change > 0.0:
            return RiskLevel.MEDIUM

        # Low risk: gap but no draught change
        return RiskLevel.LOW

    def _detect_sts(self, ais_positions: list[dict]) -> list[STSTransfer]:
        """Detect ship-to-ship transfers from AIS proximity data."""
        # In production: analyze vessel proximity, speed changes, and mooring patterns
        return []

    def _analyze_port_calls(self, ais_positions: list[dict]) -> list[PortCall]:
        """Identify port calls and check against sanctioned countries."""
        calls = []
        for pos in ais_positions:
            if pos.get("in_port"):
                country = pos.get("country", "").upper()
                calls.append(PortCall(
                    port_name=pos.get("port", "Unknown"),
                    country=country,
                    arrival=datetime.fromisoformat(pos["timestamp"]),
                    is_sanctioned_country=country in SANCTIONED_COUNTRIES,
                    risk_level=RiskLevel.HIGH if country in SANCTIONED_COUNTRIES else RiskLevel.NONE,
                ))
        return calls
