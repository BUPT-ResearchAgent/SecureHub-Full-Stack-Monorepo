# Status: real

from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter()

CTFTIME_API = "https://ctftime.org/api/v1"

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)


@router.get("")
async def get_ctf_events(limit: int = 15):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CTFTIME_API}/events/", params={"limit": limit}, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch CTFtime: {str(e)}"
            )


@router.get("/{event_id}")
async def get_ctf_event_detail(event_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CTFTIME_API}/events/{event_id}/", timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch CTFtime: {str(e)}"
            )
