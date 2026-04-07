from typing import List
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.agent_session import AgentSession
from app.schemas.chat import ChatMessageResponse
from app.schemas.rest import MessageCreateBody, SessionPatchRequest
from app.schemas.session import SessionCreateResponse, SessionResponse
from app.services.chat_reply_stream import stream_assistant_sse
from app.services.session_messages import create_user_message_and_enqueue, list_messages_for_session
from app.services.session_services import (
    create_agent_session,
    delete_session_by_id,
    list_agent_sessions,
    patch_agent_session,
)
from app.api.v1.deps import get_session_or_404

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    session = await create_agent_session(db)
    response.headers["Location"] = f"/api/v1/sessions/{session.id}"
    return SessionCreateResponse(id=session.id)


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=200, ge=1, le=500),
) -> List[SessionResponse]:
    """List sessions newest-first (by last update)."""
    return await list_agent_sessions(db, limit=limit)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session: AgentSession = Depends(get_session_or_404),
) -> SessionResponse:
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def patch_session(
    body: SessionPatchRequest,
    session: AgentSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    return await patch_agent_session(session, body, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session: AgentSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    deleted = await delete_session_by_id(session, db)
    if not deleted:
        raise HTTPException(status_code=400, detail="Failed to delete session")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/messages/assistant-stream")
async def assistant_reply_stream(
    _session: AgentSession = Depends(get_session_or_404),
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


@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
async def list_session_messages(
    session: AgentSession = Depends(get_session_or_404),
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> List[ChatMessageResponse]:
    messages = await list_messages_for_session(db, session_id=session.id, limit=limit, before=before)
    return messages


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_message(
    body: MessageCreateBody,
    session: AgentSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    return await create_user_message_and_enqueue(db, session_id=session.id, content=body.content)
