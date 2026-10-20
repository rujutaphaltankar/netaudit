from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.api.uploads import read_validated_upload

from app.core.config import Settings, get_settings
from app.parsers.registry import VENDOR_DISPLAY_NAMES, get_parser
from app.schemas.api import ConfigParseResponse, ErrorResponse, VendorInfo
from app.schemas.normalized import Vendor
from app.services.config_pipeline import analyze_config

router = APIRouter(tags=["configs"])

_ERRORS = {400: {"model": ErrorResponse}, 413: {"model": ErrorResponse},
           415: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


@router.get("/vendors", response_model=list[VendorInfo])
def list_vendors() -> list[VendorInfo]:
    out = []
    for vendor in Vendor:
        parser = get_parser(vendor)
        out.append(VendorInfo(id=vendor, display_name=VENDOR_DISPLAY_NAMES[vendor],
                              supported=parser is not None,
                              parser_version=parser.version if parser else None))
    return out


@router.post("/configs/parse", response_model=ConfigParseResponse, responses=_ERRORS)
async def parse_config(
    file: UploadFile = File(..., description="Network device configuration (text)."),
    vendor: str = Form("auto", description="'auto' or a vendor id such as cisco_ios / juniper_junos."),
    force_vendor: bool = Form(False, description="Parse as the selected vendor even if detection disagrees."),
    settings: Settings = Depends(get_settings),
    _user=Depends(get_current_user),
) -> ConfigParseResponse:
    """Validate, detect/confirm the vendor, parse and normalize a configuration file.

    Stateless preview: nothing is persisted; the upload is held in memory only. Requires login.
    """
    upload = await read_validated_upload(file, settings)
    return analyze_config(upload, vendor.strip().lower() or "auto", force_vendor)
