# Status: real

"""Run immutable, redacted benchmark manifests deterministically."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.benchmark.benchmark import BenchmarkCaseResult, BenchmarkDatasetVersion, BenchmarkRun
from app.db.models.identity.user import User
from app.repositories.benchmark.benchmark_repository import BenchmarkRepository
from app.repositories.governance.governance import GovernanceRepository
from app.schemas.benchmark import (
    BenchmarkCaseResultDTO,
    BenchmarkDatasetDTO,
    BenchmarkDatasetListDTO,
    BenchmarkRunDTO,
    BenchmarkRunRequest,
)

_ADMIN_ROLE = "administrator"
_CODE_REVISION = "gap13-benchmark-runner-v1"
_ROOT = Path(__file__).resolve().parents[3] / "benchmarks"
_DATASETS: tuple[tuple[str, str, str], ...] = (
    ("content_relevance", "1.0.0", "content-relevance-v1.json"),
    ("api_misuse", "1.0.0", "api-misuse-v1.json"),
    ("fairness", "1.0.0", "fairness-v1.json"),
)


class BenchmarkDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class BenchmarkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BenchmarkRepository(session)
        self.governance_repo = GovernanceRepository(session)

    async def bootstrap_default_datasets(self) -> None:
        """Populate empty ORM-created test databases with the frozen manifests.

        Production migration 1085 seeds equivalent immutable rows.  This
        helper never invokes a provider and is deliberately not exposed as a
        public write endpoint.
        """

        now = datetime.now(UTC)
        for kind, semantic_version, manifest_name in _DATASETS:
            if await self.repo.get_dataset_by_kind_version(kind=kind, semantic_version=semantic_version):
                continue
            manifest = self._load_manifest(manifest_name)
            await self.repo.create_dataset(
                kind=kind,
                semantic_version=semantic_version,
                manifest_hash=_sha256_file(_ROOT / "manifests" / manifest_name),
                label_schema_version=str(manifest["label_schema_version"]),
                manifest_path=f"manifests/{manifest_name}",
                data_path=f"data/{manifest['data_file']}",
                source_note=str(manifest["source_note"]),
                status="frozen",
                frozen_at=now,
                created_by=None,
            )

    async def list_datasets(self, *, actor: User) -> BenchmarkDatasetListDTO:
        await self._require_admin(actor)
        return BenchmarkDatasetListDTO(items=[self._dataset_dto(row) for row in await self.repo.list_datasets()])

    async def run_dataset(
        self, *, actor: User, dataset_id: UUID, payload: BenchmarkRunRequest
    ) -> BenchmarkRunDTO:
        await self._require_admin(actor)
        dataset = await self.repo.get_dataset(dataset_id)
        if dataset is None or dataset.status != "frozen":
            raise BenchmarkDomainError("BENCHMARK_DATASET_NOT_FROZEN", "基准数据集不存在或未冻结。", 404)
        if payload.formula_version != "binary-confusion-v1":
            raise BenchmarkDomainError("BENCHMARK_CONFIG_INVALID", "当前冻结数据集只允许 binary-confusion-v1。", 422)
        manifest = self._load_manifest_path(dataset.manifest_path)
        manifest_hash = _sha256_file(_safe_child_path(_ROOT, dataset.manifest_path))
        if manifest_hash != dataset.manifest_hash:
            raise BenchmarkDomainError(
                "BENCHMARK_REPRODUCIBILITY_MISMATCH", "manifest 指纹与冻结记录不一致，已拒绝运行。", 409
            )
        if manifest.get("dataset_kind") != dataset.kind or manifest.get("semantic_version") != dataset.semantic_version:
            raise BenchmarkDomainError("BENCHMARK_REPRODUCIBILITY_MISMATCH", "manifest 元数据与冻结记录不一致。", 409)
        frozen_thresholds = dict(manifest.get("thresholds") or {})
        if payload.thresholds and payload.thresholds != frozen_thresholds:
            raise BenchmarkDomainError("BENCHMARK_CONFIG_INVALID", "基准阈值已冻结，不能在运行时覆盖。", 422)
        data_path = _safe_child_path(_ROOT, dataset.data_path)
        if _sha256_file(data_path) != manifest.get("data_sha256"):
            raise BenchmarkDomainError(
                "BENCHMARK_REPRODUCIBILITY_MISMATCH", "数据指纹与 manifest 不一致，已拒绝运行。", 409
            )
        rows = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            raise BenchmarkDomainError("BENCHMARK_CONFIG_INVALID", "冻结数据集不能为空。", 422)
        now = datetime.now(UTC)
        thresholds = frozen_thresholds
        config_fingerprint = _fingerprint(
            {
                "manifest_hash": manifest_hash,
                "formula_version": payload.formula_version,
                "thresholds": thresholds,
                "code_revision": _CODE_REVISION,
            }
        )
        run = await self.repo.create_run(
            dataset_version_id=dataset.id,
            formula_version=payload.formula_version,
            thresholds=thresholds,
            code_revision=_CODE_REVISION,
            config_fingerprint=config_fingerprint,
            status="running",
            summary={},
            failure_code=None,
            executed_by=actor.id,
            started_at=now,
            finished_at=None,
        )
        positive = str(manifest.get("positive_label"))
        matrix: Counter[str] = Counter()
        group_counts: dict[str, int] = defaultdict(int)
        failures: list[dict[str, str]] = []
        case_rows: list[BenchmarkCaseResult] = []
        for row in rows:
            required = {"case_key", "expected_label", "predicted_label", "group_key", "group_value"}
            if not required.issubset(row):
                run.status = "failed"
                run.failure_code = "BENCHMARK_CONFIG_INVALID"
                run.finished_at = datetime.now(UTC)
                await self.session.flush()
                raise BenchmarkDomainError("BENCHMARK_CONFIG_INVALID", "冻结数据行缺少必要标签字段。", 422)
            expected = str(row["expected_label"])
            predicted = str(row["predicted_label"])
            decision = _binary_decision(expected=expected, predicted=predicted, positive=positive)
            failure_reason = "label_mismatch" if decision in {"fp", "fn"} else None
            case = await self.repo.create_case_result(
                run_id=run.id,
                case_key=str(row["case_key"]),
                expected_label=expected,
                predicted_label=predicted,
                decision=decision,
                failure_reason=failure_reason,
                redacted_payload_reference=f"{dataset.kind}:{row['case_key']}",
            )
            case_rows.append(case)
            matrix[decision] += 1
            group_counts[f"{row['group_key']}:{row['group_value']}"] += 1
            if failure_reason:
                failures.append({"case_key": str(row["case_key"]), "decision": decision})
        run.summary = {
            "dataset_kind": dataset.kind,
            "semantic_version": dataset.semantic_version,
            "manifest_hash": manifest_hash,
            "data_hash": manifest["data_sha256"],
            "label_schema_version": manifest["label_schema_version"],
            "confusion_matrix": {key: matrix[key] for key in ("tp", "tn", "fp", "fn")},
            "group_counts": dict(sorted(group_counts.items())),
            "failure_samples": failures,
            "source_note": dataset.source_note,
            "user_effect_metric": False,
        }
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="benchmark.run",
            object_type="benchmark_run",
            object_id=run.id,
            reason="执行冻结、脱敏的可复现基准。",
            result_status="completed",
            metadata={
                "dataset_version_id": str(dataset.id),
                "config_fingerprint": config_fingerprint,
                "case_count": len(case_rows),
                "contains_user_effect_metric": False,
            },
        )
        return self._run_dto(run, dataset, case_rows)

    async def get_run(self, *, actor: User, run_id: UUID) -> BenchmarkRunDTO:
        await self._require_admin(actor)
        run = await self.repo.get_run(run_id)
        if run is None:
            raise BenchmarkDomainError("BENCHMARK_RUN_NOT_FOUND", "基准运行不存在。", 404)
        dataset = await self.repo.get_dataset(run.dataset_version_id)
        if dataset is None:
            raise BenchmarkDomainError("BENCHMARK_REPRODUCIBILITY_MISMATCH", "基准运行缺少冻结数据集。", 409)
        return self._run_dto(run, dataset, await self.repo.list_case_results(run.id))

    async def _require_admin(self, actor: User) -> None:
        if not await self.governance_repo.has_active_role(user_id=actor.id, role_code=_ADMIN_ROLE):
            raise BenchmarkDomainError("ADMIN_ROLE_REQUIRED", "当前账号不具备基准治理管理员权限。")

    @staticmethod
    def _dataset_dto(row: BenchmarkDatasetVersion) -> BenchmarkDatasetDTO:
        return BenchmarkDatasetDTO(
            id=row.id,
            kind=row.kind,  # type: ignore[arg-type]
            semantic_version=row.semantic_version,
            manifest_hash=row.manifest_hash,
            label_schema_version=row.label_schema_version,
            source_note=row.source_note,
            status=row.status,  # type: ignore[arg-type]
            frozen_at=row.frozen_at,
        )

    @staticmethod
    def _run_dto(
        run: BenchmarkRun, dataset: BenchmarkDatasetVersion, cases: list[BenchmarkCaseResult] | Any
    ) -> BenchmarkRunDTO:
        return BenchmarkRunDTO(
            id=run.id,
            dataset_version_id=dataset.id,
            dataset_kind=dataset.kind,  # type: ignore[arg-type]
            dataset_version=dataset.semantic_version,
            formula_version=run.formula_version,
            thresholds=dict(run.thresholds or {}),
            code_revision=run.code_revision,
            config_fingerprint=run.config_fingerprint,
            status=run.status,  # type: ignore[arg-type]
            summary=dict(run.summary or {}),
            failure_code=run.failure_code,
            started_at=run.started_at,
            finished_at=run.finished_at,
            cases=[
                BenchmarkCaseResultDTO(
                    case_key=case.case_key,
                    expected_label=case.expected_label,
                    predicted_label=case.predicted_label,
                    decision=case.decision,  # type: ignore[arg-type]
                    failure_reason=case.failure_reason,
                    redacted_payload_reference=case.redacted_payload_reference,
                )
                for case in cases
            ],
        )

    @staticmethod
    def _load_manifest(name: str) -> dict[str, Any]:
        return BenchmarkService._load_manifest_path(f"manifests/{name}")

    @staticmethod
    def _load_manifest_path(path: str) -> dict[str, Any]:
        return json.loads(_safe_child_path(_ROOT, path).read_text(encoding="utf-8"))


def _safe_child_path(root: Path, relative: str) -> Path:
    child = (root / relative).resolve()
    if root not in child.parents:
        raise BenchmarkDomainError("BENCHMARK_CONFIG_INVALID", "基准资产路径不在受控目录内。", 422)
    return child


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _binary_decision(*, expected: str, predicted: str, positive: str) -> str:
    expected_positive = expected == positive
    predicted_positive = predicted == positive
    if expected_positive and predicted_positive:
        return "tp"
    if not expected_positive and not predicted_positive:
        return "tn"
    return "fp" if predicted_positive else "fn"
