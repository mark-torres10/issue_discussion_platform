from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import study_error_response
from app.core.staff_auth import StaffIdentityDep
from app.models.export import SessionExportManifest
from app.services.export import export_session
from app.services.sessions import StudyApiError

router = APIRouter(tags=["staff-export"])


@router.get(
    "/sessions/{session_id}/export",
    response_model=SessionExportManifest,
)
async def get_session_export(
    request: Request,
    session_id: UUID,
    staff: StaffIdentityDep,
) -> SessionExportManifest | JSONResponse:
    try:
        request_id = getattr(request.state, "request_id", None)
        return await export_session(
            session_id,
            staff.user_id,
            request_id=request_id,
        )
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )
