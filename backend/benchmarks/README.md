# T6 可复现基准

本目录只保存三个版本化、脱敏的评测资产：内容相关性、API 误用和公平阈值复核。每个 manifest 冻结数据哈希、标注规则、公式、阈值和来源说明。

这些小型评测样本不是用户数据，也不是产品效果统计；尤其 `fairness` 数据集不得被表述为真实学习者群体结果。真实评分只能经 T6 的有效同意、最小化分组和样本量门槛后计算。

运行方式（不会调用 Provider）：

```powershell
uv run python benchmarks/run_benchmarks.py --all
```

输出包含混淆矩阵、分组计数和仅由 case key 组成的失败样本。运行器会先校验 manifest 与 data 的 SHA-256；哈希不匹配即拒绝运行。哈希以 UTF-8 内容的 LF 规范换行计算，因此 Git 在 Windows 上的 CRLF 检出不会造成误报；受控资产也通过 `.gitattributes` 固定为 LF。
