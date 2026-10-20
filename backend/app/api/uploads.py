from fastapi import UploadFile

from app.core.config import Settings
from app.services.upload_validation import ValidatedUpload, validate_upload


async def read_validated_upload(file: UploadFile, settings: Settings) -> ValidatedUpload:
    try:
        data = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    return validate_upload(file.filename, data, settings)
