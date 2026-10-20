from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.db.models import AIMapping, User
from app.db.session import get_db
from app.schemas.audit import AIMappingOut, ReviewRequest
from app.services import ai_mapping as svc
from app.services.audit_service import get_audit_or_404, mapping_out

router = APIRouter(tags=["ai-review"], dependencies=[Depends(get_current_user)])


@router.post("/audits/{audit_id}/ai-mappings/generate", dependencies=[Depends(require_admin), Depends(rate_limit("ai_generate", 10, 60))])
def generate(audit_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    """Suggest meanings for the unrecognized commands of an audit (AI if configured, otherwise heuristics)."""
    return svc.generate_mappings(db, get_audit_or_404(db, audit_id), settings)


@router.get("/audits/{audit_id}/ai-mappings", response_model=list[AIMappingOut])
def for_audit(audit_id: int, db: Session = Depends(get_db)):
    return [mapping_out(m) for m in get_audit_or_404(db, audit_id).ai_mappings]


@router.get("/ai-mappings", response_model=list[AIMappingOut])
def list_mappings(status: str | None = Query(None, pattern="^(pending|approved|rejected)$"), db: Session = Depends(get_db)):
    stmt = select(AIMapping).order_by(AIMapping.id.desc()).limit(500)
    if status:
        stmt = stmt.where(AIMapping.status == status)
    return [mapping_out(m) for m in db.scalars(stmt)]


@router.post("/ai-mappings/{mapping_id}/review", response_model=AIMappingOut)
def review(mapping_id: int, body: ReviewRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    mapping = db.get(AIMapping, mapping_id)
    if mapping is None:
        raise AppError(404, "mapping_not_found", "Mapping not found.")
    return mapping_out(svc.review_mapping(db, mapping, admin, body.decision, body.note))
