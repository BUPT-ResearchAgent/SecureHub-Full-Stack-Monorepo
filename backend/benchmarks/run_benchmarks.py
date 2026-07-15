#!/usr/bin/env python3
"""Run frozen, redacted T6 benchmark manifests without a live provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFESTS = ROOT / "manifests"
DATA = ROOT / "data"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    data_path = DATA / manifest["data_file"]
    actual_hash = sha256_file(data_path)
    if actual_hash != manifest["data_sha256"]:
        raise ValueError(f"BENCHMARK_REPRODUCIBILITY_MISMATCH: {path.name}")
    positive = manifest["positive_label"]
    matrix: Counter[str] = Counter()
    group_counts: dict[str, int] = defaultdict(int)
    failures: list[dict[str, str]] = []
    for line in data_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        expected_positive = row["expected_label"] == positive
        predicted_positive = row["predicted_label"] == positive
        decision = "tp" if expected_positive and predicted_positive else "tn" if not expected_positive and not predicted_positive else "fp" if predicted_positive else "fn"
        matrix[decision] += 1
        group_counts[f"{row['group_key']}:{row['group_value']}"] += 1
        if decision in {"fp", "fn"}:
            failures.append({"case_key": row["case_key"], "decision": decision})
    return {
        "kind": manifest["dataset_kind"],
        "semantic_version": manifest["semantic_version"],
        "manifest_hash": sha256_file(path),
        "confusion_matrix": {key: matrix[key] for key in ("tp", "tn", "fp", "fn")},
        "group_counts": dict(sorted(group_counts.items())),
        "failure_samples": failures,
        "source_note": manifest["source_note"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="单个 manifest 路径")
    parser.add_argument("--all", action="store_true", help="运行三个冻结 manifest")
    args = parser.parse_args()
    if bool(args.manifest) == bool(args.all):
        parser.error("必须指定 --manifest 或 --all 之一")
    manifests = [args.manifest] if args.manifest else sorted(MANIFESTS.glob("*.json"))
    print(json.dumps([run_manifest(path) for path in manifests], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
