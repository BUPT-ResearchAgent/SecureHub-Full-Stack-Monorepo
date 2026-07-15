# 可复现基准契约（VG-01 / T6）

状态：`real`。基准资产在 `backend/benchmarks/`，只包含版本化、脱敏、非用户效果评测数据。

## 冻结资产

| kind | manifest | 数据 | 说明 |
| --- | --- | --- | --- |
| `content_relevance` | `manifests/content-relevance-v1.json` | `data/content-relevance-v1.jsonl` | 冻结相关性标注复现 |
| `api_misuse` | `manifests/api-misuse-v1.json` | `data/api-misuse-v1.jsonl` | 冻结、脱敏规则判定复现；没有凭据/IP/原始请求 |
| `fairness` | `manifests/fairness-v1.json` | `data/fairness-v1.jsonl` | 阈值复核逻辑评测；不是实际学习者群体效果 |

每个 manifest 冻结数据 SHA-256、标注规则、positive label、公式与阈值。运行器和服务在读取前校验 manifest/data 哈希；不一致固定拒绝 `BENCHMARK_REPRODUCIBILITY_MISMATCH`。

## HTTP 与持久化

- `GET /api/v1/benchmarks/datasets`：管理员读取 frozen dataset version。
- `POST /api/v1/benchmarks/datasets/{id}/runs`：管理员执行 `binary-confusion-v1`，阈值不能运行时覆盖。
- `GET /api/v1/benchmarks/runs/{id}`：管理员读取运行记录、混淆矩阵、分组计数和红化失败 case key。

`benchmark_dataset_versions`、`benchmark_runs`、`benchmark_case_results` 固化 dataset/version/hash/config/code revision/status。case result 只保存标签、TP/TN/FP/FN、failure reason 和 redacted payload reference；不保存原始负载。

## 可复现命令

```powershell
cd SecureHub-Full-Stack-Monorepo/backend
uv run python benchmarks/run_benchmarks.py --all
```

该命令不调用 LLM/Provider，不读取真实用户数据。输出明确 `user_effect_metric: false`；不得将这些评测结果写成竞品百分比或用户效果。
