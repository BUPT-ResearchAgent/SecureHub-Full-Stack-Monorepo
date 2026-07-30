# Status: real

"""Curated visualization briefs for all WEBSEC-101 knowledge points."""

from __future__ import annotations

from dataclasses import dataclass


VISUALIZATION_TYPES = (
    "architecture",
    "attack-defense",
    "checklist",
    "flowchart",
    "matrix",
    "sequence",
)


@dataclass(frozen=True)
class WebSecurityVisualPrompt:
    kp_id: str
    title: str
    visualization_type: str
    scene_brief: str
    required_labels: tuple[str, ...]
    recommended_size: str = "1024x1024"

    def render(
        self,
        *,
        custom_prompt: str | None = None,
        visualization_type: str | None = None,
    ) -> str:
        requested_type = visualization_type or self.visualization_type
        focus = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else self.scene_brief
        labels = "、".join(f"“{label}”" for label in self.required_labels)
        return (
            f"为 WEBSEC-101 的“{self.title}”制作一张{requested_type}类型的网络安全教学信息图。"
            f"核心内容：{focus}。画面必须准确表达因果与数据流，不渲染可直接复用的攻击载荷。"
            f"只使用这些简短中文标签：{labels}。"
            "采用克制的瑞士编辑设计：米白背景、深海军蓝文字、蓝色表示正常流、红色表示攻击流、"
            "绿色表示防御与校验；清晰箭头、等宽代码占位符、充足留白、16:9 横向构图。"
            "不出现人物、品牌标志、水印、伪造界面截图或无关装饰，中文必须清楚可读。"
        )


_PROMPTS = (
    WebSecurityVisualPrompt(
        "http-basics",
        "HTTP 请求与响应",
        "sequence",
        "浏览器经由 DNS 与 TLS 向 Web 服务发送请求，服务端返回状态行、响应头与响应体，并标出无状态请求边界。",
        ("浏览器", "请求行", "请求头", "请求体", "状态码", "响应体"),
    ),
    WebSecurityVisualPrompt(
        "same-origin",
        "同源策略与 CORS",
        "architecture",
        "以协议、主机、端口三元组判断同源；跨源请求先经过浏览器策略与预检，再由服务端 CORS 响应头授权。",
        ("同源", "跨源", "预检请求", "允许来源", "浏览器拦截"),
    ),
    WebSecurityVisualPrompt(
        "cookie-session",
        "Cookie 与 Session",
        "sequence",
        "登录后服务端创建会话，浏览器保存带安全属性的 Cookie，后续请求携带会话标识并在服务端校验。",
        ("登录", "会话标识", "HttpOnly", "SameSite", "服务端会话"),
    ),
    WebSecurityVisualPrompt(
        "sql-injection",
        "SQL 注入与参数化查询",
        "attack-defense",
        "对比字符串拼接让不可信输入改变查询结构，与参数化查询把 SQL 模板和数据分离的防御路径。",
        ("不可信输入", "字符串拼接", "查询结构", "参数绑定", "安全查询"),
    ),
    WebSecurityVisualPrompt(
        "sql-injection-blind",
        "盲注与侧信道",
        "flowchart",
        "展示布尔差异与时间差异如何泄露真假信息，以及统一错误、参数化查询与超时监控如何阻断侧信道。",
        ("输入探测", "布尔差异", "时间差异", "统一响应", "异常监控"),
    ),
    WebSecurityVisualPrompt(
        "xss-reflected",
        "反射型 XSS",
        "attack-defense",
        "恶意参数进入请求后被页面原样反射并在浏览器解释；对比上下文输出编码与内容安全策略的防御链。",
        ("恶意参数", "服务端反射", "浏览器解释", "输出编码", "内容安全策略"),
    ),
    WebSecurityVisualPrompt(
        "xss-stored",
        "存储型 XSS",
        "sequence",
        "不可信内容先写入数据库，随后被多个访问者页面读取和解释；入口净化、出口编码与 CSP 形成分层防御。",
        ("内容提交", "数据库", "多用户读取", "内容净化", "输出编码"),
    ),
    WebSecurityVisualPrompt(
        "xss-dom",
        "DOM 型 XSS",
        "flowchart",
        "前端脚本从 URL 或消息读取不可信数据并写入危险 DOM 接口；对比 textContent 与安全模板。",
        ("不可信源", "前端脚本", "危险接口", "textContent", "安全模板"),
    ),
    WebSecurityVisualPrompt(
        "csrf",
        "CSRF 与请求真实性",
        "sequence",
        "受害者浏览器自动携带站点 Cookie 发起跨站敏感请求；服务端以 CSRF Token、SameSite 与来源校验确认请求意图。",
        ("恶意站点", "自动携带 Cookie", "敏感操作", "CSRF Token", "来源校验"),
    ),
    WebSecurityVisualPrompt(
        "file-upload",
        "文件上传安全",
        "checklist",
        "上传文件依次经过大小、扩展名、真实 MIME、文件签名、重命名、隔离存储与内容扫描，最后只以受控方式提供。",
        ("大小限制", "类型校验", "随机命名", "隔离存储", "内容扫描", "受控访问"),
    ),
    WebSecurityVisualPrompt(
        "ssrf",
        "SSRF 与出站访问控制",
        "architecture",
        "用户提供 URL 进入服务端抓取器，攻击流试图访问环回、内网与云元数据；防御流执行协议、域名、DNS 与地址段校验。",
        ("用户 URL", "服务端请求", "内网资源", "地址校验", "出站代理"),
    ),
    WebSecurityVisualPrompt(
        "deserialization",
        "不安全反序列化",
        "flowchart",
        "不可信序列化数据进入对象恢复过程并可能触发危险类型或回调；安全方案采用白名单数据模型、签名与纯数据格式。",
        ("不可信数据", "对象恢复", "危险类型", "签名校验", "数据白名单"),
    ),
    WebSecurityVisualPrompt(
        "rce",
        "远程代码执行链",
        "attack-defense",
        "从输入边界、解释器或命令执行到系统权限的攻击链，并展示参数化 API、最小权限、沙箱和审计告警的分层阻断。",
        ("输入边界", "解释器", "系统权限", "最小权限", "沙箱", "审计告警"),
    ),
    WebSecurityVisualPrompt(
        "auth-bypass",
        "认证绕过",
        "flowchart",
        "请求从身份声明进入认证、会话、授权三道关口，对比仅前端判断或信任用户参数与服务端集中校验。",
        ("身份声明", "认证", "会话校验", "授权", "拒绝访问"),
    ),
    WebSecurityVisualPrompt(
        "waf-bypass",
        "WAF 边界与绕过",
        "architecture",
        "请求在编码规范化后经过 WAF 与应用校验，说明 WAF 只能作为纵深防御，业务层参数化与权限控制仍是核心。",
        ("请求规范化", "WAF", "应用校验", "误报漏报", "纵深防御"),
    ),
    WebSecurityVisualPrompt(
        "secure-coding",
        "安全编码生命周期",
        "flowchart",
        "需求、设计、编码、评审、测试、发布与监控形成闭环，每个阶段都有可执行的安全门禁与反馈。",
        ("安全需求", "威胁建模", "代码评审", "安全测试", "发布门禁", "持续监控"),
    ),
    WebSecurityVisualPrompt(
        "owasp-top10",
        "OWASP Top 10 风险地图",
        "matrix",
        "以身份、输入、数据、配置、供应链五个防御域组织常见 Web 风险，突出风险之间的关联和共同控制措施。",
        ("身份", "输入", "数据", "配置", "供应链", "共同控制"),
    ),
)

WEBSEC_VISUAL_PROMPTS: dict[str, WebSecurityVisualPrompt] = {
    prompt.kp_id: prompt for prompt in _PROMPTS
}


def get_websec_visual_prompt(kp_id: str) -> WebSecurityVisualPrompt:
    normalized = kp_id.strip().lower()
    try:
        return WEBSEC_VISUAL_PROMPTS[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown WEBSEC-101 knowledge point: {kp_id}") from exc


__all__ = [
    "VISUALIZATION_TYPES",
    "WEBSEC_VISUAL_PROMPTS",
    "WebSecurityVisualPrompt",
    "get_websec_visual_prompt",
]
