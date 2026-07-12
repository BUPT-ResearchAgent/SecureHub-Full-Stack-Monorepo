# Status: real

from fastapi import APIRouter

from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/ping", response_model=MessageResponse)
def ping() -> MessageResponse:
    return MessageResponse(message="pong")
