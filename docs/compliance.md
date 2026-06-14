# SecureHub 多源采集合规手册

> 一页纸合规底线。所有采集 / 数据导入 / EvidenceDrawer 展示必须遵守本文件。
>
> 适用对象：成员 C（主责）+ 成员 A（ingestion service）+ 成员 B（EvidenceDrawer / SourcePanel）。
> 上游铁律：`.codex/AGENTS.md §3.9` + `§10.5.9` + `CLAUDE.md §2.1`。
> 法律免责：本项目用于教学研究 / 比赛演示 / 非营利学习用途。任何对外发布、商业化、对外服务前必须由法务重新评审。

---

## 1. 通用红线（任一违反直接撤销 PR）

| # | 红线 | 例外 |
|---|---|---|
| 1 | 不绕登录 | — |
| 2 | 不绕验证码 / 滑块 / 人机识别 | — |
| 3 | 不绕 Cloudflare / WAF / 反爬 | — |
| 4 | 不用代理轮转做反规避 | per-domain 节流 OK |
| 5 | 不做大规模 / 高并发抓取 | 默认 ≤ 2 并发 + 2s 延迟 |
| 6 | 不批量搬运完整侵权 / 付费内容 | 仅入摘要 + 链接 + 引用切片 |
| 7 | 不抓取明确禁止自动化访问的页面 | robots.txt Disallow → 直接跳过 |
| 8 | 不丢失 metadata（platform / source_url / author / published_at / fetched_at / license / rights_note） | 缺一不可入库 |

---

## 2. 数据三级分类（决定能不能进 git）

| 等级 | 类型 | 处理方式 | git 策略 |
|---|---|---|---|
| **L1 完全开放** | 公共许可证（OWASP CC BY-SA、GitHub MIT、Apache 2.0、CC0、政府公开政策原文） | 入 `documents` + `chunks`，metadata 标 license | `data/seed/L1/` 随仓库提交 |
| **L2 公开但版权不明** | CSDN / 博客园 / 个人博客 / 微信公众号 / 社媒帖子 / 视频转写 | 仅入 `documents.metadata` + `chunks.metadata.excerpt`（摘要 ≤ 300 字 / 视频 ≤ 30 秒转写） + `source_url` + `rights_note="excerpt only, link to source"` | `data/seed/L2/` 随仓库（但内容已是摘要） |
| **L3 受限 / 付费 / 教材** | 商业教材 / 付费课程 / 教学视频原版 / 内部文档 / 包含个人信息的资料 | 仅个人本地处理，**不入主库**；可入 `data/raw/private/` 做离线 RAG 实验 | `.gitignore` 必须包含；CI 检查无 L3 文件意外提交 |

---

## 3. 各平台采集策略

| 平台 / 来源 | 工具 | 等级 | 合规要点 | 入库 domain |
|---|---|---|---|---|
| OWASP | Scrapling / manual | L1 | 遵守 CC BY-SA，保留 source_url 与 license | `course_websec` |
| PortSwigger Web Security Academy | Scrapling / manual | L2 | 公开学习引用，仅入摘要 + 章节 + URL，不全文转载 | `course_websec` |
| GitHub README / Docs | GitHub raw API / Scrapling | L1 / L2 | 遵守仓库 LICENSE；MIT / Apache / BSD 等可入正文，GPL / 商用受限仅入摘要 | `course_websec` / `competition` |
| CSDN / 博客园 / 个人博客 | Scrapling | L2 | 摘要 + 链接 + author + published_at；rights_note="excerpt, link to source" | `course_websec` |
| Bilibili | MediaCrawler / manual | L2 | 仅入视频 metadata（title / video_id / author / duration）+ 字幕摘要 ≤ 30s；不下载视频本体；不绕区域限制 | `course_websec` / `competition` |
| 知乎 | MediaCrawler / manual | L2 | 仅入问答 metadata + 答案摘要 ≤ 300 字 + 链接；不绕登录 | `course_websec` / `job` |
| 小红书 | MediaCrawler / manual | L2 | 仅入笔记 metadata + 摘要 + 链接；不批量爬，单次会话 ≤ 50 篇 | `job` / `competition` |
| 抖音 / 快手 / 微博 / 贴吧 | MediaCrawler / manual | L2 | 同知乎策略；优先小规模 + 手动登录后导出 | `news` / `course_websec` |
| 微信公众号 | manual / 授权导入 | L2 | 优先作者授权；未授权仅入摘要 + 链接 | `policy` / `news` |
| CVE / CNVD / NVD | 官方 API / RSS | L1 | 公开漏洞信息；**不抓 PoC 利用代码**（铁律 §3.9 + 安全护栏） | `news` / `course_websec` |
| CTFtime | 官方 API | L1 | 已接入 `endpoints/ctftime.py` | `competition` |
| arXiv | RSS + 官方 PDF 下载 | L1 | 遵守 arXiv terms；PDF 经 MinerU 转 Markdown 后入库 | `paper` |
| 招聘 JD（公开页面） | Scrapling / manual | L2 | 不绕登录；不抓简历或求职者信息；仅入 JD 公开内容 | `job` |

---

## 4. MediaCrawler / MindSpider 专项声明

这两个项目本身定位为"学习研究 / 非商业用途"。本项目对它们的使用必须满足：

1. **仅使用其离线 export**（JSON / JSONL / CSV / SQLite），不在生产环境长期运行其 daemon。
2. **不复用其平台专用 DB schema**（`xhs_note` / `bili_video` / `zhihu_answer` / `topics` 等）—— 统一经 `source_normalizer` 入 SecureHub data-layer v2。
3. **不包装其能力**作为对外服务 / 商业产品 / API 接口。
4. **采集规模**：单次会话每平台 ≤ 200 条；总累计 ≤ 5000 条（够 demo + RAG 训练，不构成实质性数据搬运）。
5. **保留来源**：每条记录 metadata 含 platform / source_url / author / published_at / fetched_at / `rights_note="collected via MediaCrawler for educational use"`。
6. **演示与文档显著位置**标注："本项目仅用于教学研究与比赛演示，不对外发布数据"。

---

## 5. EvidenceDrawer / SourcePanel 展示规则（前端）

成员 B 实现时必须满足：

1. 每个 evidence chunk 显示 `platform` + `source_url`（可点击）+ `author` + `published_at`。
2. `rights_note` 非空时以小字 / 灰色标注，例如 "OWASP CC BY-SA 4.0" / "Excerpt only, link to source"。
3. 摘要长度 ≤ 300 字；超出折叠 + "查看完整原文（外链）"按钮。
4. **不**展示完整的版权资料正文 —— 即便 chunks 表里有，UI 也只渲染前 300 字 + 链接。
5. 评估证据来源时，`reliability` < 0.5 的 chunk 加"⚠ 来源可信度较低"提示。
6. 视频类来源（B站 / 抖音等）显示视频缩略图 + timestamp（"00:15:30 处"）跳转外链。

---

## 6. CI / PR 检查项

PR 模板（A6）的合规自检条目：

- [ ] 本 PR 涉及采集 / 数据导入 / EvidenceDrawer？
- [ ] 若是 → metadata 字段是否齐全（platform / source_url / author / published_at / fetched_at / rights_note）？
- [ ] 若是 → 是否设置了 `CRAWL_RESPECT_ROBOTS=true` + 节流 + 限制并发？
- [ ] 若是 → 是否禁用了 `solve_cloudflare` / proxy rotation / 登录绕过？
- [ ] 若涉及 L3 资料 → 是否在 `.gitignore` 中？是否仅本地处理？
- [ ] 若批量入库 → 单次规模是否 ≤ 200 / 平台 + ≤ 5000 累计？

---

## 7. 出现以下情况立即停手 → 升级

- 平台返回大量 403 / 429 / CAPTCHA 挑战 → 节流不够，立即停并加大延迟
- 收到平台投诉 / DMCA / 律师函 → 立刻停止该 source 的采集，记录在 `Workout/session_log.md`，升级项目负责人
- 发现采集到的资料含个人敏感信息（电话 / 身份证 / 地址 / 简历）→ 立即删除入库记录 + storage_objects 物理删除，记录在 session_log
- 发现采集到的资料含攻击载荷 / 0day 利用代码 → 立即删除 + 触发 outcome_evaluator 二次审核，记录在 session_log

---

## 8. 法律 / 演示文档显著位置标注模板

A3 配套文档 / PPT / 演示视频片尾必须包含：

> 本项目（SecureHub / CyberLadder）为教学研究与比赛演示用途。
> 项目使用了以下开源 / 公开资源：OWASP（CC BY-SA 4.0）、PortSwigger Web Security Academy（学习用途）、GitHub 开源项目（各自 LICENSE）、CTFtime API、arXiv RSS。
> 项目采集了少量公开中文社媒资料用于课程知识库建设，遵守公开 / 节流 / 保留来源 / 仅摘要原则，所有内容来源在系统内可追溯。
> 不对外发布采集到的原始数据，不用于任何商业用途。
> 项目使用 Claude Code / Codex / Cursor 等 AI 编码助手协助开发，使用讯飞星火作为主大模型，符合 A3 赛题要求。

---

*Last updated: 2026-06-09。本清单与 `.codex/AGENTS.md §3.9 / §10.5.9` 保持一致。修改本文件必须同步更新 AGENTS.md。*
