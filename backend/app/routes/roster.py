import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.config import Settings, get_settings
from app.deps import get_import_service
from app.exceptions import RosterImportError
from app.schemas import PreviewOut, UploadOut
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/roster", tags=["roster"])


@router.post("/preview", response_model=PreviewOut)
async def preview_roster(
    request: Request,
    file: UploadFile = File(...),
    service: ImportService = Depends(get_import_service),
    settings: Settings = Depends(get_settings),
) -> PreviewOut:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.max_upload_bytes * 2:
                raise RosterImportError("Upload exceeds maximum allowed size")
        except ValueError:
            pass
    content = await file.read()
    return service.preview_workbook(
        filename=file.filename or "roster.xlsx",
        content=content,
    )


@router.get("", response_model=list[UploadOut])
def list_roster_uploads(
    service: ImportService = Depends(get_import_service),
) -> list[UploadOut]:
    service.discard_stale_pending(max_age=timedelta(hours=24))
    return service.list_uploads()


@router.post("/{upload_id}/commit", response_model=UploadOut)
def commit_roster(
    upload_id: uuid.UUID,
    service: ImportService = Depends(get_import_service),
) -> UploadOut:
    return service.commit_upload(upload_id)


@router.delete("/{upload_id}", status_code=204)
def discard_roster(
    upload_id: uuid.UUID,
    service: ImportService = Depends(get_import_service),
) -> None:
    service.discard_upload(upload_id)
