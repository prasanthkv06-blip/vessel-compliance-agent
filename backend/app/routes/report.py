import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from ..orchestrator import ComplianceOrchestrator
from ..models.report import ComplianceReport
from ..models.check_request import VesselCheckRequest
from ..report_engine.generator import ReportGenerator

router = APIRouter(prefix="/api/v1/report", tags=["report"])
orchestrator = ComplianceOrchestrator()
report_generator = ReportGenerator()

# In-memory cache: imo -> last generated ComplianceReport
_report_cache: dict[str, ComplianceReport] = {}


# ── Existing endpoints (IMO query-param, sample data) ────────────────────────

@router.post("/generate", response_model=ComplianceReport)
async def generate_report(imo: str, created_by: str = ""):
    try:
        report = await orchestrator.generate_report(imo, created_by)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/html")
async def generate_report_html(imo: str, created_by: str = ""):
    try:
        report = await orchestrator.generate_report(imo, created_by)
        html = report_generator.render_html(report)
        return HTMLResponse(content=html)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate/pdf")
async def generate_report_pdf(imo: str, created_by: str = ""):
    try:
        report = await orchestrator.generate_report(imo, created_by)
        pdf_path = report_generator.render_pdf(report)
        return {"pdf_path": pdf_path, "report_id": report.report_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── New endpoints — user supplies vessel + owner details ──────────────────────

@router.post("/check", response_model=ComplianceReport, summary="Run compliance check from user input")
async def check_vessel(req: VesselCheckRequest):
    """
    Accept vessel name, IMO, flag and owner/operator(s) directly from the user
    and run a full compliance check against real OFAC/EU sanctions lists.
    """
    try:
        report = await orchestrator.generate_report_from_input(req)
        _report_cache[req.imo] = report
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/check/html", summary="Run compliance check and return HTML report")
async def check_vessel_html(req: VesselCheckRequest):
    try:
        report = await orchestrator.generate_report_from_input(req)
        _report_cache[req.imo] = report
        html = report_generator.render_html(report)
        return HTMLResponse(content=html)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/check/pdf", summary="Run compliance check and download PDF report")
async def check_vessel_pdf(req: VesselCheckRequest):
    try:
        report = await orchestrator.generate_report_from_input(req)
        _report_cache[req.imo] = report
        pdf_path = report_generator.render_pdf(report)
        filename = f"VCR-{report.vessel.imo}-{report.vessel.name.replace(' ', '_')}.pdf"
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── GET endpoints — view cached report as HTML/PDF ───────────────────────────

@router.get("/view/{imo}/html", summary="View cached HTML report in browser")
async def view_report_html(imo: str):
    """Returns the last generated HTML report for a given IMO (cached in memory)."""
    report = _report_cache.get(imo)
    if not report:
        # Try fallback to sample data
        try:
            report = await orchestrator.generate_report(imo)
            _report_cache[imo] = report
        except ValueError:
            raise HTTPException(status_code=404, detail=f"No cached report for IMO {imo}. Run a compliance check first.")
    html = report_generator.render_html(report)
    return HTMLResponse(content=html)


@router.get("/view/{imo}/pdf", summary="Download cached PDF report")
async def view_report_pdf(imo: str):
    report = _report_cache.get(imo)
    if not report:
        try:
            report = await orchestrator.generate_report(imo)
            _report_cache[imo] = report
        except ValueError:
            raise HTTPException(status_code=404, detail=f"No cached report for IMO {imo}.")
    pdf_path = report_generator.render_pdf(report)
    filename = f"VCR-{report.vessel.imo}-{report.vessel.name.replace(' ', '_')}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
