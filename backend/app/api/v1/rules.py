from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.rules.loader import load_catalog
from app.schemas.audit import RuleCatalogOut

router = APIRouter(tags=["rules"], dependencies=[Depends(get_current_user)])


@router.get("/rules", response_model=RuleCatalogOut)
def list_rules() -> RuleCatalogOut:
    return RuleCatalogOut.model_validate(load_catalog().model_dump())
