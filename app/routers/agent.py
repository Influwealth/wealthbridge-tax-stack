"""
Caffeine Agent router.

POST /agent/chat — run a conversational inference turn
GET  /agent/tools — list available tool schemas
GET  /agent/status — check agent availability
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import models
from app.rbac import require_permission
from caffeine_agent.agent import CaffeineAgent
from caffeine_agent.tools import TOOL_SCHEMAS

router = APIRouter(prefix="/agent", tags=["caffeine-agent"])

_agent = CaffeineAgent()


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class AgentChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    system: Optional[str] = None


class AgentChatResponse(BaseModel):
    response: str
    tool_calls_made: list
    model: str
    status: str


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    payload: AgentChatRequest,
    _: models.User = Depends(require_permission("filings:read")),
):
    messages = [m.model_dump() for m in payload.messages]
    result = _agent.run(messages=messages, system=payload.system)
    return AgentChatResponse(**result)


@router.get("/tools")
def list_tools(_: models.User = Depends(require_permission("filings:read"))):
    return TOOL_SCHEMAS


@router.get("/status")
def agent_status(_: models.User = Depends(require_permission("filings:read"))):
    return {
        "available": _agent.is_available(),
        "model": _agent.model,
        "tool_count": len(TOOL_SCHEMAS),
    }
