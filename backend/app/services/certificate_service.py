"""Certificate Matrix Service — Phase 1.

Builds a CertificateMatrix from:
  1. Raw certificate list scraped from Equasis (if available)
  2. Fallback: infer expected certificates from vessel type and populate
     as "not_found" so the report always shows a complete matrix.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from ..models.report import Certificate, CertificateMatrix

# Certificates required by all vessels
_UNIVERSAL_CERTS = [
    "Safety Management Certificate (SMC)",
    "Document of Compliance (DOC)",
    "International Ship Security Certificate (ISSC / ISPS)",
    "Maritime Labour Certificate (MLC 2006)",
    "Certificate of Civil Liability (CLC)",
    "International Bunker Pollution Prevention Certificate",
    "International Oil Pollution Prevention Certificate (IOPP)",
    "Cargo Ship Safety Equipment Certificate",
    "Cargo Ship Safety Radio Certificate",
    "International Load Line Certificate",
]

# Additional certs for tankers
_TANKER_CERTS = [
    "International Certificate of Fitness (IGC / IBC)",
    "Document of Compliance for Carriage of Dangerous Goods",
]

_CERT_VALIDITY_YEARS = {
    "Safety Management Certificate (SMC)": 5,
    "Document of Compliance (DOC)": 5,
    "International Ship Security Certificate (ISSC / ISPS)": 5,
    "Maritime Labour Certificate (MLC 2006)": 5,
    "International Oil Pollution Prevention Certificate (IOPP)": 5,
    "International Load Line Certificate": 5,
    "Certificate of Civil Liability (CLC)": 1,
    "International Bunker Pollution Prevention Certificate": 1,
    "Cargo Ship Safety Equipment Certificate": 1,
    "Cargo Ship Safety Radio Certificate": 1,
}


def _parse_iso(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _cert_status(expiry: Optional[date]) -> str:
    if expiry is None:
        return "not_found"
    today = date.today()
    if expiry < today:
        return "expired"
    if expiry <= today + timedelta(days=90):
        return "expiring_soon"
    return "valid"


def build_certificate_matrix(
    raw_certs: list[dict],
    vessel_type: str = "",
) -> CertificateMatrix:
    """
    Build CertificateMatrix.
    raw_certs: list of {name, issuer, issue_date, expiry_date} from Equasis.
    """
    required = list(_UNIVERSAL_CERTS)
    vtype = vessel_type.lower()
    if any(t in vtype for t in ["tanker", "lng", "lpg", "chemical", "gas"]):
        required += _TANKER_CERTS

    # Index scraped certs by normalised name
    scraped: dict[str, dict] = {}
    for c in raw_certs:
        key = c.get("name", "").upper().strip()
        if key:
            scraped[key] = c

    certs: list[Certificate] = []
    for cert_name in required:
        # Try exact match, then substring match
        match = scraped.get(cert_name.upper())
        if not match:
            for sk, sv in scraped.items():
                if cert_name[:12].upper() in sk or sk in cert_name.upper():
                    match = sv
                    break

        if match:
            expiry = _parse_iso(match.get("expiry_date"))
            issue  = _parse_iso(match.get("issue_date"))
            status = _cert_status(expiry)
            certs.append(Certificate(
                name=cert_name,
                issuer=match.get("issuer"),
                issue_date=match.get("issue_date"),
                expiry_date=match.get("expiry_date"),
                status=status,
            ))
        else:
            # Not found in Equasis data — mark as unknown
            certs.append(Certificate(
                name=cert_name,
                status="not_found",
            ))

    expiring = sum(1 for c in certs if c.status == "expiring_soon")
    expired  = sum(1 for c in certs if c.status == "expired")
    not_fnd  = sum(1 for c in certs if c.status == "not_found")
    all_valid = (expired == 0 and expiring == 0)

    return CertificateMatrix(
        certificates=certs,
        all_valid=all_valid,
        expiring_count=expiring,
        expired_count=expired,
        not_found_count=not_fnd,
    )
