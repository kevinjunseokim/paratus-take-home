from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_agent_service
from app.schemas import ChatRequest, ChatResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    service: AgentService = Depends(get_agent_service),
) -> ChatResponse:
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    for message in body.messages:
        if message.role not in {"user", "assistant"}:
            raise HTTPException(status_code=400, detail="role must be user or assistant")
    result = service.chat([m.model_dump() for m in body.messages])
    return ChatResponse(reply=result["reply"], tool_traces=result["tool_traces"])
