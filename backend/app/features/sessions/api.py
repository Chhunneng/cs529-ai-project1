from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_pdf_artifact_for_session_or_404, get_session_or_404
from app.core.config import settings
from app.db.session import get_db_session
from app.models.chat_session import ChatSession
from app.models.pdf_artifact import PdfArtifact
from app.schemas.chat import ChatMessageResponse, PendingRepliesResponse
from app.schemas.rest import SessionPatchRequest, SessionMessageCreateBody
from app.schemas.pagination import PaginatedSessionsResponse
from app.schemas.session import SessionCreateResponse, SessionResponse
from app.features.sessions.assistant_sse import stream_assistant_sse
from app.features.sessions.chat_reply_redis import list_pending_user_message_ids
from app.features.sessions.chat_messages import (
    create_session_turn_and_enqueue,
    list_messages_for_session,
)
from app.features.pdf_generation.pdf_artifacts import unlink_pdf_artifact_file
from app.features.sessions.service import (
    create_chat_session,
    delete_session_by_id,
    list_chat_sessions,
    patch_chat_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    session = await create_chat_session(db)
    response.headers["Location"] = f"/api/v1/sessions/{session.id}"
    return SessionCreateResponse(id=session.id)


@router.get("", response_model=PaginatedSessionsResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PaginatedSessionsResponse:
    total = int(await db.scalar(select(func.count()).select_from(ChatSession)) or 0)
    rows = await list_chat_sessions(db, limit=limit, offset=offset)
    return PaginatedSessionsResponse(items=list(rows), total=total)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session: ChatSession = Depends(get_session_or_404),
) -> SessionResponse:
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def patch_session(
    body: SessionPatchRequest,
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    return await patch_chat_session(session, body, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    deleted = await delete_session_by_id(session, db)
    if not deleted:
        raise HTTPException(status_code=400, detail="Failed to delete session")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/messages/assistant-stream")
async def assistant_reply_stream(
    _session: ChatSession = Depends(get_session_or_404),
    user_message_id: uuid.UUID = Query(..., description="User message id for this turn"),
) -> StreamingResponse:
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        stream_assistant_sse(_session.id, user_message_id),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/{session_id}/messages/pending-replies", response_model=PendingRepliesResponse)
async def list_pending_replies(
    session: ChatSession = Depends(get_session_or_404),
) -> PendingRepliesResponse:
    raw = await list_pending_user_message_ids(session_id=session.id)
    ids: list[uuid.UUID] = []
    for s in raw:
        try:
            ids.append(uuid.UUID(s))
        except ValueError:
            continue
    return PendingRepliesResponse(pending_user_message_ids=ids)


@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
async def list_session_messages(
    session: ChatSession = Depends(get_session_or_404),
    limit: int = Query(default=100, ge=1, le=200),
    before: datetime | None = Query(default=None),
    anchor: Literal["start", "end"] = Query(
        default="end",
        description="With before unset: 'end' returns the newest messages; 'start' returns the oldest.",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> List[ChatMessageResponse]:
    return await list_messages_for_session(
        db, session_id=session.id, limit=limit, before=before, anchor=anchor
    )


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_message(
    body: SessionMessageCreateBody,
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    return await create_session_turn_and_enqueue(
        db,
        session_id=session.id,
        content=body.content,
        resume_template_id=body.resume_template_id,
        resume_id=body.resume_id,
        job_description_id=body.job_description_id,
    )


# @router.delete(
#     "/{session_id}/messages/{message_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
# )
# async def delete_session_message(
#     message_id: uuid.UUID,
#     session: ChatSession = Depends(get_session_or_404),
#     db: AsyncSession = Depends(get_db_session),
# ) -> Response:
#     ok = await delete_chat_message_for_session(
#         db, session_id=session.id, message_id=message_id
#     )
#     if not ok:
#         raise HTTPException(status_code=404, detail="Message not found")
#     return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/pdf-artifacts/{pdf_artifact_id}/file")
async def download_session_pdf_artifact(
    pdf_artifact_id: uuid.UUID,
    artifact: PdfArtifact = Depends(get_pdf_artifact_for_session_or_404),
    disposition: Literal["inline", "attachment"] = Query(
        default="attachment",
        description='Use "inline" for browser preview (e.g. iframe); "attachment" encourages download.',
    ),
) -> FileResponse:
    root = Path(settings.storage.artifacts_dir).resolve()
    path = (root / artifact.storage_relpath).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=404, detail="PDF artifact not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF file missing on disk")

    return FileResponse(
        path,
        media_type=artifact.mime_type,
        filename=f"resume-{pdf_artifact_id}.pdf",
        content_disposition_type=disposition,
    )


@router.delete(
    "/{session_id}/pdf-artifacts/{pdf_artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session_pdf_artifact(
    artifact: PdfArtifact = Depends(get_pdf_artifact_for_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    unlink_pdf_artifact_file(storage_relpath=artifact.storage_relpath)
    await db.delete(artifact)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
