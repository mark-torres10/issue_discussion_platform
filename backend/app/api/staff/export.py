"""Staff session export routes.

Staff-authenticated endpoints for exporting durable session data for analysis
or archival.
"""

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
    """Export a session manifest for staff review.

  Requires a Supabase JWT in the ``Authorization: Bearer`` header. Requests
  that include a ``participant_capability`` cookie are rejected. The staff
  identity must have export permission for the requested session.

  Parameters
  ----------
  request : Request
      Incoming HTTP request; ``request.state.request_id`` is forwarded to the
      export audit trail when present.
  session_id : UUID
      Session to export.
  staff : StaffIdentity
      Authenticated staff user resolved from the bearer token.

  Returns
  -------
  SessionExportManifest or JSONResponse
      Export manifest with artifact references on success, or a JSON error
      body when authentication, authorization, or export assembly fails.
  """
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
