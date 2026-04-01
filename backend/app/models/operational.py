from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .vessel import RiskLevel

class AISGap(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_hours: float
    start_location: str
    end_location: str
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    draught_change: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW

class STSTransfer(BaseModel):
    timestamp: datetime
    location: str
    lat: float
    lon: float
    partner_vessel_imo: Optional[str] = None
    partner_vessel_name: Optional[str] = None
    is_dark_sts: bool = False
    is_high_risk_location: bool = False
    risk_level: RiskLevel = RiskLevel.LOW

class PortCall(BaseModel):
    port_name: str
    country: str
    arrival: datetime
    departure: Optional[datetime] = None
    is_sanctioned_country: bool = False
    risk_level: RiskLevel = RiskLevel.NONE

class OperationalRiskSummary(BaseModel):
    ais_gaps: list[AISGap] = []
    sts_transfers: list[STSTransfer] = []
    port_calls: list[PortCall] = []
    ais_spoofing_detected: bool = False
    highest_risk: RiskLevel = RiskLevel.NONE
