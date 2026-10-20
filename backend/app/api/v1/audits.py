from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.uploads import read_validated_upload
from app.core.config import Settings, get_settings
from app.core.ratelimit import rate_limit
from app.db.models import User
from app.db.session import get_db
from app.rules.engine import evaluate_config
from app.schemas.audit import AuditComparison, AuditDetail, AuditItem, AuditPage, DashboardStats
from app.services import audit_service as svc
from app.services.config_pipeline import analyze_config
from app.services.report_pdf import build_report

router = APIRouter(tags=["audits"], dependencies=[Depends(get_current_user)])


@router.post("/audits", response_model=AuditDetail, status_code=201,
             dependencies=[Depends(rate_limit("audit_upload", 20, 60))])
async def create_audit(
    file: UploadFile = File(..., description="Network device configuration (text)."),
    vendor: str = Form("auto"), force_vendor: bool = Form(False),
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings), admin: User = Depends(require_admin),
) -> AuditDetail:
    """Parse the configuration, run all compliance rules and store the result (raw config is not stored)."""
    upload = await read_validated_upload(file, settings)
    parsed = analyze_config(upload, vendor.strip().lower() or "auto", force_vendor)
    audit = svc.persist_audit(db, admin, parsed, evaluate_config(parsed.result.config))
    return svc.to_detail(audit)


@router.get("/audits", response_model=AuditPage)
def list_audits(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                vendor: str | None = None, q: str | None = None, db: Session = Depends(get_db)) -> AuditPage:
    rows, total = svc.list_audits(db, page, page_size, vendor, q)
    return AuditPage(items=[svc.to_item(a) for a in rows], total=total, page=page, page_size=page_size)


@router.get("/audits/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)) -> DashboardStats:
    return svc.dashboard_stats(db)


@router.get("/audits/compare", response_model=AuditComparison)
def compare(base: int, target: int, db: Session = Depends(get_db)) -> AuditComparison:
    return svc.compare_audits(svc.get_audit_or_404(db, base), svc.get_audit_or_404(db, target))


@router.get("/audits/{audit_id}", response_model=AuditDetail)
def get_audit(audit_id: int, db: Session = Depends(get_db)) -> AuditDetail:
    return svc.to_detail(svc.get_audit_or_404(db, audit_id))


@router.delete("/audits/{audit_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_audit(audit_id: int, db: Session = Depends(get_db)) -> Response:
    db.delete(svc.get_audit_or_404(db, audit_id))
    db.commit()
    return Response(status_code=204)


@router.get("/audits/{audit_id}/report.pdf")
def report(audit_id: int, db: Session = Depends(get_db)) -> Response:
    audit = svc.get_audit_or_404(db, audit_id)
    return Response(content=build_report(audit), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="netaudit-report-{audit.id}.pdf"'})
