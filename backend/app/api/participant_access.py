from typing import Annotated

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core.dependencies import study_error_response
from app.models.session import AccessExchangeRequest, ParticipantSessionView
from app.services.capability import (
    CAPABILITY_COOKIE_NAME,
    CSRF_HEADER_NAME,
    capability_cookie_attributes,
    sign_capability_payload,
)
from app.services.sessions import StudyApiError, exchange_access

router = APIRouter(prefix="/v1/participant-access", tags=["participant-access"])


@router.post("/exchange", response_model=ParticipantSessionView)
def participant_access_exchange(
    request: Request,
    response: Response,
    body: AccessExchangeRequest,
) -> ParticipantSessionView | JSONResponse:
    try:
        view, capability, cross_site = exchange_access(body)
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )

    payload = {
        "session_id": str(capability.session_id),
        "capability_id": capability.capability_id,
        "writer_role": capability.writer_role,
        "csrf_token": capability.csrf_token,
    }
    signed = sign_capability_payload(payload)
    response.set_cookie(
        key=CAPABILITY_COOKIE_NAME,
        value=signed,
        **capability_cookie_attributes(cross_site=cross_site),
    )
    response.headers[CSRF_HEADER_NAME] = capability.csrf_token
    return view
