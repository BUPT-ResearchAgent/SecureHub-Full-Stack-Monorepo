# Status: real

"""HTTP adapters for frozen reproducible benchmark execution."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.benchmark import BenchmarkDatasetListDTO, BenchmarkRunDTO, BenchmarkRunRequest
from app.services.benchmark.benchmark_service import BenchmarkDomainError, BenchmarkService

router = APIRouter(prefix="/benchmarks")


def _raise_domain_error(error: BenchmarkDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/datasets", response_model=BenchmarkDatasetListDTO)
async def list_datasets(session: SessionDep, user: RequiredCurrentUserDep) -> BenchmarkDatasetListDTO:
    try:
        return await BenchmarkService(session).list_datasets(actor=user)
    except BenchmarkDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/datasets/{dataset_id}/runs", response_model=BenchmarkRunDTO, status_code=201)
async def run_dataset(
    dataset_id: UUID,
    payload: BenchmarkRunRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> BenchmarkRunDTO:
    try:
        result = await BenchmarkService(session).run_dataset(actor=user, dataset_id=dataset_id, payload=payload)
        await session.commit()
        return result
    except BenchmarkDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/runs/{run_id}", response_model=BenchmarkRunDTO)
async def get_run(run_id: UUID, session: SessionDep, user: RequiredCurrentUserDep) -> BenchmarkRunDTO:
    try:
        return await BenchmarkService(session).get_run(actor=user, run_id=run_id)
    except BenchmarkDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
