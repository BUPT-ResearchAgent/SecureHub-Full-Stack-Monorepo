# SecureHub LLM Fallback Strategy

> 演示日讯飞星火限流 / 超时 / 拒答时怎么办的**预先决策书**。不要在演示当天临时开会。
>
> 适用对象：成员 A（实现）+ 全员（演示日值守）。
> 上游依赖：`.env.example` 的 `LLM_PRIMARY` + `LLM_FALLBACK_CHAIN` + `HARNESS_MOCK_MODE`；`runtime/harness/base.py` 的 fallback 钩子。

---

## 1. 三层降级体系

```
[L0]  主链路：讯飞星火（A3 硬要求，演示主用）
        ↓ 失败触发条件见 §2
[L1]  模型 fallback：DeepSeek → Qwen
        ↓ 全部失败 / 演示环境无 KEY
[L2]  Harness mock：HARNESS_MOCK_MODE=true，返回 fixture
```

**核心原则**：
- 演示视频里主路径必须真讯飞，**演示前 24 小时**才切回 L0 主链。
- 开发期 / CI / 离线 demo 默认走 L2 mock；mock 数据从 `backend/app/db/seeds/seed_smoke.py` 同源 fixture 取。
- L1 fallback 仅作为"主链单次失败"的临时降级；连续 5 次失败必须人工介入，不允许长时间跑在 fallback 上。

---

## 2. 降级触发条件（逐场景）

| 场景 | 触发信号 | 降级到 | 是否上报 |
|---|---|---|---|
| 讯飞 429 限流 | HTTP 429 / 错误码 10013 | L1 DeepSeek | 是（session_log + Toast） |
| 讯飞 502 / 网络异常 | HTTP 5xx / timeout | L1 DeepSeek | 是 |
| 讯飞内容拒答（合规拦截） | 返回内容含拒答标志 / 空 content | **不降级**，直接返回 InsufficientEvidence 或 GuardrailBlocked | 是 |
| 讯飞超时 > `HARNESS_TIMEOUT_SECONDS` | 计时器到期 | L1 DeepSeek（带新超时） | 是 |
| DeepSeek 同样失败 | 同上 | L1 Qwen | 是（连续 3 次升 P1） |
| 全部 L1 失败 / 无 KEY | 链尾 | L2 mock（仅 dev/CI） | 演示日**严禁** |
| 演示日 KEY 配额耗尽 | 余额接口 | 立即停演 + 紧急充值流程 | P0 立即 |

**关键细节**：
- "内容拒答"不能降级 —— 评委会问"为什么换个模型就给答了"。要按防幻觉原则返回 InsufficientEvidence 或 GuardrailBlocked。
- L2 mock 不允许出现在演示视频。CI / 单元测试 / 截图脚本可以。

---

## 3. 降级实现位置（架构决策）

降级层放在 `backend/app/llm/`，**不**放在 `runtime/harness/`。理由：

1. Harness 负责 skill 执行流程（retrieve → llm → quality_check → log_run），不应该感知模型选择。
2. LLM 客户端是降级的天然边界 —— `app/llm/client.py` 暴露 `chat()` / `chat_stream()` 接口，内部按 `LLM_FALLBACK_CHAIN` 顺序尝试。
3. 这样 Harness 在 `agent_runs.token_usage` 里只记录"最终成功的模型 ID + 链路尝试次数"，trace 清晰。

伪代码骨架：

```python
# backend/app/llm/client.py
# Status: planned

class LLMClient:
    def __init__(self, providers: list[Provider]):
        self.providers = providers  # 按 LLM_FALLBACK_CHAIN 顺序

    async def chat(self, prompt, *, stream=False) -> ChatResult:
        attempts: list[Attempt] = []
        for p in self.providers:
            try:
                result = await p.chat(prompt, stream=stream, timeout=HARNESS_TIMEOUT_SECONDS)
                if self._is_refusal(result):
                    raise GuardrailBlocked("LLM refused content")
                return ChatResult(result, attempts + [Attempt(p.name, "success")])
            except (RateLimitError, TimeoutError, NetworkError) as e:
                attempts.append(Attempt(p.name, type(e).__name__))
                continue  # 尝试下一个 provider
        # 全部失败
        raise AllProvidersFailed(attempts)

    @staticmethod
    def _is_refusal(text) -> bool:
        # 检测讯飞 / DeepSeek 的标准拒答标志
        ...
```

`agent_runs.token_usage` 字段约定：

```json
{
  "provider": "deepseek",           // 实际成功的
  "attempts": ["xfyun:429", "deepseek:success"],
  "prompt_tokens": 1024,
  "completion_tokens": 512,
  "model": "deepseek-chat",
  "fallback_used": true
}
```

---

## 4. mock 模式（L2）触发条件

`HARNESS_MOCK_MODE=true` 时：

- `MockLLM.chat()` 从 `backend/app/runtime/harness/fixtures.py` 返回预制响应
- `MockRetriever.retrieve()` 从 `seed_smoke.py` 同源 chunks 返回 top_k
- `MockQualityCheck.check()` 固定返回 0.85

何时使用：
- `uv run pytest` 时（CI 必走）
- 本地 dev 无讯飞 KEY 时（`.env` 不填 XFYUN_*）
- 离线 demo / 视频截图脚本

何时**禁止**使用：
- 演示日（视频录制 / 现场答辩）
- 生产环境（即便项目目前没生产）
- A3 评委演示前 24 小时回归测试

---

## 5. 演示日值守预案

### 演示前 24 小时
- [ ] 切换 `.env`：`HARNESS_MOCK_MODE=false` + `LLM_PRIMARY=xfyun`
- [ ] 检查讯飞 KEY 余额 / TPM 上限
- [ ] 跑一遍完整 demo 故事（A4 storyboard），录屏存档作为 backup
- [ ] 准备本地 mock 视频作为最终兜底

### 演示前 1 小时
- [ ] 现场网络可达性测试（讯飞 endpoint ping）
- [ ] 跑 1 次画像构建 + 1 次资源生成，确认无限流
- [ ] 后端 logs 实时 tail，准备截图

### 演示中
- 如出现单次 502 / 429 / 超时 → Harness 已自动降级 DeepSeek，演示可以继续，**不要停**
- 如出现连续 3 次失败 → 主持人圆场过场，技术值守切换到"播放预录视频"
- 如出现内容拒答 → 演示"防幻觉机制起作用了，系统拒绝生成无依据内容"（**反而是亮点**，转化为答辩话术）

### 演示后
- 在 `Workout/session_log.md` 记录全部降级事件 + 触发原因 + 处理结果

---

## 6. 容易踩的坑

| 坑 | 后果 | 防范 |
|---|---|---|
| 把 `HARNESS_MOCK_MODE=true` 留在演示分支 | 演示翻车 | PR 模板加 checkbox "mock 模式已关闭" |
| 多个 provider 用同一个 API base | 一个挂全挂 | 各 provider 独立配置 endpoint |
| fallback 不记录 attempts | 排查降级问题没数据 | `token_usage.attempts` 必填 |
| 把"内容拒答"当 502 重试 | 浪费 token + 评委困惑 | `_is_refusal()` 单独分支，不进 retry |
| 演示前一晚才切讯飞 | 配置变更未充分验证 | 24 小时前切换 + 完整回归 |
| 现场 Wi-Fi 不可靠 | 主链不通 | 现场至少 2 路网络（Wi-Fi + 4G/5G 热点） |

---

*Last updated: 2026-06-09。本文件与 `.env.example` / `backend/app/llm/` / `runtime/harness/base.py` 三处保持同步；变更必须双签 A + 项目负责人。*
