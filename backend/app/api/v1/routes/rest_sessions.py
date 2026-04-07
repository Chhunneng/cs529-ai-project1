from typing import List
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionMaker, get_db_session
from app.models.agent_session import AgentSession
from app.schemas.chat import ChatMessageResponse
from app.schemas.rest import MessageCreateBody, SessionPatchRequest
from app.schemas.session import SessionCreateResponse, SessionResponse
from app.services.chat_reply_stream import stream_assistant_sse
from app.services.session_delete import delete_session_by_id
from app.services.session_messages import create_user_message_and_enqueue, list_messages_for_session
from app.api.v1.deps import get_session_or_404

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _insert_agent_session(db: AsyncSession) -> AgentSession:
    session = AgentSession(state_json={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    session = await _insert_agent_session(db)
    response.headers["Location"] = f"/api/v1/sessions/{session.id}"
    return SessionCreateResponse(id=session.id)


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=200, ge=1, le=500),
) -> List[SessionResponse]:
    """List sessions newest-first (by last update)."""
    result = await db.execute(
        select(AgentSession).order_by(AgentSession.updated_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return sessions


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
    if body.selected_resume_id is not None:
        session.selected_resume_id = body.selected_resume_id
    if body.active_jd_id is not None:
        session.active_jd_id = body.active_jd_id
    if body.state_json is not None:
        session.state_json = body.state_json
    await db.commit()
    await db.refresh(session)
    return session


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
