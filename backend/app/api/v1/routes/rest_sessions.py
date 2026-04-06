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

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _insert_agent_session(db: AsyncSession) -> AgentSession:
    session = AgentSession(state_json={})
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session_rest(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    session = await _insert_agent_session(db)
    response.headers["Location"] = f"/api/v1/sessions/{session.id}"
    return SessionCreateResponse(id=session.id)


@router.api_route("/create", methods=["GET", "HEAD"], include_in_schema=False)
async def sessions_create_must_be_post() -> None:
    """Avoid matching ``/{{session_id}}`` with session_id=\"create\" (UUID parse errors)."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Create a session with POST /api/v1/sessions or POST /api/v1/sessions/create.",
        headers={"Allow": "POST"},
    )


@router.post("/create", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session_rest_alias(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    session = await _insert_agent_session(db)
    response.headers["Location"] = f"/api/v1/sessions/{session.id}"
    return SessionCreateResponse(id=session.id)


@router.get("", response_model=list[SessionResponse])
async def list_sessions_rest(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[SessionResponse]:
    """List sessions newest-first (by last update)."""
    result = await db.execute(
        select(AgentSession).order_by(AgentSession.updated_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        SessionResponse(
            id=s.id,
            created_at=s.created_at,
            updated_at=s.updated_at,
            selected_resume_id=s.selected_resume_id,
            active_jd_id=s.active_jd_id,
            state_json=s.state_json or {},
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_rest(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
) -> SessionResponse:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        id=session.id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        selected_resume_id=session.selected_resume_id,
        active_jd_id=session.active_jd_id,
        state_json=session.state_json or {},
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def patch_session_rest(
    session_id: uuid.UUID,
    body: SessionPatchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.selected_resume_id is not None:
        session.selected_resume_id = body.selected_resume_id
    if body.active_jd_id is not None:
        session.active_jd_id = body.active_jd_id
    if body.state_json is not None:
        session.state_json = body.state_json
    await db.commit()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        selected_resume_id=session.selected_resume_id,
        active_jd_id=session.active_jd_id,
        state_json=session.state_json or {},
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_rest(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    deleted = await delete_session_by_id(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/messages/assistant-stream")
async def assistant_reply_stream(
    session_id: uuid.UUID,
    user_message_id: uuid.UUID = Query(..., description="User message id for this turn"),
) -> StreamingResponse:
    async with AsyncSessionMaker() as db:
        result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Session not found")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        stream_assistant_sse(session_id, user_message_id),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_session_messages(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageResponse]:
    sess = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    if sess.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = await list_messages_for_session(db, session_id=session_id, limit=limit, before=before)
    return [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            message=m.message,
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_message(
    session_id: uuid.UUID,
    body: MessageCreateBody,
    db: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await create_user_message_and_enqueue(db, session_id=session_id, content=body.content)
