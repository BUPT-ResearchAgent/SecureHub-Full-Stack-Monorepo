from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

from app.schemas.research import ResearchItemType


def evidence(title: str, url: str, source_type: str, updated_at: str) -> dict[str, str]:
    return {
        "title": title,
        "url": url,
        "source_type": source_type,
        "updated_at": updated_at,
    }


class ResearchRepository:
    def __init__(self) -> None:
        self._items: dict[str, list[dict[str, Any]]] = {
            "fund": [
                {
                    "id": "fund-nsfc-ai-security",
                    "title": "国家自然科学基金青年项目 · 网络空间安全 F0207",
                    "source": "国家自然科学基金委员会",
                    "level": "国家级",
                    "amount": "30 万",
                    "deadline": "2026-06-15",
                    "direction": "AI 安全",
                    "match_score": 94,
                    "tags": ["青年项目", "大模型安全", "基础研究"],
                    "summary": "面向大模型攻击面、提示注入防护、数据投毒检测等前沿问题，适合形成论文和原型系统。",
                    "requirements": ["申请人需具备明确研究基础", "提交立项依据、研究内容、技术路线和年度计划", "建议准备近三年代表性成果"],
                    "recommendation_reason": "与你当前 AI 安全与竞赛项目积累匹配，且有较强论文产出空间。",
                    "evidence_sources": [evidence("国家自然科学基金项目指南", "https://www.nsfc.gov.cn/", "基金指南", "2026-03-01")],
                    "updated_at": "2026-04-20",
                    "favorited": True,
                    "subscribed": True,
                    "compared": True,
                },
                {
                    "id": "fund-edu-industry",
                    "title": "教育部产学合作协同育人项目 · 网安实验教学",
                    "source": "教育部高等教育司",
                    "level": "部级",
                    "amount": "2-5 万",
                    "deadline": "2026-05-30",
                    "direction": "工控安全",
                    "match_score": 81,
                    "tags": ["产学合作", "教学改革", "实验平台"],
                    "summary": "支持网络安全实验教学、实训平台建设、课程资源开发与企业实践协作。",
                    "requirements": ["需有校内指导教师牵头", "明确企业协作单位", "提交课程或平台建设方案"],
                    "recommendation_reason": "适合将现有实战靶场和课程材料沉淀为可验收成果。",
                    "evidence_sources": [evidence("教育部产学合作协同育人项目平台", "https://cxhz.hep.com.cn/", "项目平台", "2026-04-12")],
                    "updated_at": "2026-04-18",
                    "favorited": False,
                    "subscribed": False,
                    "compared": False,
                },
                {
                    "id": "fund-provincial-critical-infra",
                    "title": "省部级重点研发计划 · 关键信息基础设施安全专项",
                    "source": "省科技厅",
                    "level": "省部级",
                    "amount": "50-100 万",
                    "deadline": "2026-07-01",
                    "direction": "零信任",
                    "match_score": 87,
                    "tags": ["重点研发", "关基保护", "零信任"],
                    "summary": "聚焦工业互联网、政务云、能源系统中的身份可信、访问控制和持续监测。",
                    "requirements": ["鼓励企业联合申报", "需说明应用场景和验收指标", "需提供示范部署计划"],
                    "recommendation_reason": "零信任方向与政策场景契合度高，适合作为挑战杯后续延展项目。",
                    "evidence_sources": [evidence("省科技计划项目申报通知", "https://example.edu.cn/research/provincial-plan", "申报通知", "2026-04-05")],
                    "updated_at": "2026-04-16",
                    "favorited": False,
                    "subscribed": True,
                    "compared": False,
                },
                {
                    "id": "fund-huawei-huyanglin",
                    "title": "CCF-华为胡杨林基金 · 网络安全专项",
                    "source": "中国计算机学会",
                    "level": "企业合作",
                    "amount": "5-15 万",
                    "deadline": "滚动申报",
                    "direction": "隐私计算",
                    "match_score": 76,
                    "tags": ["企业合作", "青年学者", "工程探索"],
                    "summary": "支持面向真实产业问题的探索性研究，适合小团队快速验证隐私计算工程化方案。",
                    "requirements": ["提交问题定义和预期成果", "鼓励开源代码或技术报告", "需说明产业价值"],
                    "recommendation_reason": "资助规模适中，适合作为论文方法到系统原型的过渡资金。",
                    "evidence_sources": [evidence("CCF 基金项目公告", "https://www.ccf.org.cn/", "基金公告", "2026-03-28")],
                    "updated_at": "2026-04-10",
                    "favorited": False,
                    "subscribed": False,
                    "compared": False,
                },
            ],
            "news": [
                {
                    "id": "news-usenix-accepted",
                    "title": "USENIX Security 2026 录用论文列表公布",
                    "source": "USENIX Association",
                    "source_type": "学术会议",
                    "published_at": "2026-04-21",
                    "summary": "本轮录用论文覆盖大模型安全、供应链攻击检测、隐私增强系统等方向，可作为选题趋势参考。",
                    "url": "https://www.usenix.org/conference/usenixsecurity26",
                    "tags": ["顶会", "论文录用", "AI 安全"],
                    "evidence_sources": [evidence("USENIX Security 2026", "https://www.usenix.org/conference/usenixsecurity26", "会议官网", "2026-04-21")],
                    "updated_at": "2026-04-21",
                    "read": False,
                    "favorited": False,
                },
                {
                    "id": "news-ai-security-center",
                    "title": "高校成立 AI 安全联合研究中心",
                    "source": "高校网络空间安全学院",
                    "source_type": "机构动态",
                    "published_at": "2026-04-18",
                    "summary": "中心将开放大模型安全评测、对齐鲁棒性和数据治理相关课题，适合关注开放实验室合作。",
                    "url": "https://example.edu.cn/news/ai-security-center",
                    "tags": ["开放课题", "AI 安全"],
                    "evidence_sources": [evidence("学院新闻公告", "https://example.edu.cn/news/ai-security-center", "机构公告", "2026-04-18")],
                    "updated_at": "2026-04-19",
                    "read": False,
                    "favorited": True,
                },
                {
                    "id": "news-csa-roadmap",
                    "title": "网络空间安全技术路线图更新",
                    "source": "中国网络空间安全协会",
                    "source_type": "行业组织",
                    "published_at": "2026-04-12",
                    "summary": "路线图强调零信任、关基保护、数据要素安全和软件供应链安全的交叉研究价值。",
                    "url": "https://example.org/roadmap/security-2026",
                    "tags": ["政策趋势", "零信任", "供应链安全"],
                    "evidence_sources": [evidence("技术路线图摘要", "https://example.org/roadmap/security-2026", "行业报告", "2026-04-12")],
                    "updated_at": "2026-04-13",
                    "read": True,
                    "favorited": False,
                },
            ],
            "innovation": [
                {
                    "id": "innovation-llm-alignment-security",
                    "title": "大模型对齐安全与越狱防护",
                    "direction": "AI 安全",
                    "growth": 38,
                    "window": "近6个月",
                    "representative_papers": ["Jailbreaking LLMs via Multi-turn Adversarial Chains", "Safety Alignment under Adversarial Prompts"],
                    "representative_teams": ["清华大学网络研究院", "UC Berkeley Security Lab"],
                    "engineering_difficulty": "中",
                    "academic_value": "高",
                    "summary": "从攻击样本构造、对齐评测、防护策略三个层面形成快速增长的研究链条。",
                    "recommendation_reason": "可与现有提示注入检测原型直接衔接，适合形成论文和竞赛演示。",
                    "evidence_sources": [evidence("AI Safety Benchmark Survey", "https://example.org/papers/ai-safety-survey", "综述论文", "2026-04-08")],
                    "updated_at": "2026-04-20",
                },
                {
                    "id": "innovation-zero-trust-iot",
                    "title": "工业互联网零信任访问控制",
                    "direction": "零信任",
                    "growth": 24,
                    "window": "近12个月",
                    "representative_papers": ["Zero-Trust for Industrial IoT: A Systematic Review"],
                    "representative_teams": ["上交大网安学院", "NUS Systems Security Group"],
                    "engineering_difficulty": "高",
                    "academic_value": "中高",
                    "summary": "研究重点从身份认证扩展到细粒度授权、持续评估和协议适配。",
                    "recommendation_reason": "政策牵引强，适合和关基保护基金项目联动。",
                    "evidence_sources": [evidence("Industrial IoT Security Review", "https://example.org/papers/zero-trust-iot", "论文", "2026-03-29")],
                    "updated_at": "2026-04-18",
                },
                {
                    "id": "innovation-post-quantum",
                    "title": "后量子密码迁移评估",
                    "direction": "后量子密码",
                    "growth": 31,
                    "window": "近12个月",
                    "representative_papers": ["Measuring PQC Migration Risks in TLS Ecosystems"],
                    "representative_teams": ["中科院信工所", "ETH Zurich"],
                    "engineering_difficulty": "中高",
                    "academic_value": "高",
                    "summary": "围绕算法替换、协议兼容和性能评估形成可实验的工程研究路径。",
                    "recommendation_reason": "适合作为安全测评或协议分析方向的中长期课题。",
                    "evidence_sources": [evidence("NIST PQC Standardization", "https://csrc.nist.gov/projects/post-quantum-cryptography", "标准进展", "2026-04-01")],
                    "updated_at": "2026-04-15",
                },
            ],
            "paper": [
                {
                    "id": "paper-jailbreak-chain",
                    "title": "Jailbreaking LLMs via Multi-turn Adversarial Chains",
                    "venue": "USENIX Security",
                    "year": 2026,
                    "authors": ["L. Chen", "M. Zhang", "A. Smith"],
                    "citation_count": 42,
                    "abstract": "The paper studies multi-turn jailbreak construction and proposes a benchmark for measuring model refusal robustness.",
                    "reading_guide": "重点关注威胁模型、攻击链构造和评测指标，可直接借鉴到提示注入检测项目。",
                    "doi_url": "https://doi.org/10.0000/usenix.2026.001",
                    "pdf_url": "https://example.org/papers/jailbreak-chain.pdf",
                    "tags": ["AI 安全", "大模型", "评测"],
                    "evidence_sources": [evidence("USENIX Security Paper Page", "https://www.usenix.org/conference/usenixsecurity26", "会议论文", "2026-04-21")],
                    "updated_at": "2026-04-21",
                    "favorited": True,
                    "in_reading_list": True,
                    "compared": True,
                },
                {
                    "id": "paper-zero-trust-iot-review",
                    "title": "Zero-Trust for Industrial IoT: A Systematic Review",
                    "venue": "IEEE S&P",
                    "year": 2026,
                    "authors": ["R. Wang", "Y. Liu"],
                    "citation_count": 28,
                    "abstract": "A systematic review of zero-trust architecture in industrial IoT with deployment constraints and evaluation gaps.",
                    "reading_guide": "适合作为工控安全选题综述入口，重点阅读架构分类和开放问题。",
                    "doi_url": "https://doi.org/10.0000/sp.2026.018",
                    "pdf_url": None,
                    "tags": ["零信任", "工控安全", "综述"],
                    "evidence_sources": [evidence("IEEE S&P Proceedings", "https://www.ieee-security.org/TC/SP2026/", "会议论文", "2026-04-10")],
                    "updated_at": "2026-04-18",
                    "favorited": False,
                    "in_reading_list": False,
                    "compared": False,
                },
                {
                    "id": "paper-supply-chain-graph",
                    "title": "Supply Chain Attack Detection with Graph Learning",
                    "venue": "NDSS",
                    "year": 2026,
                    "authors": ["K. Zhao", "P. Kumar", "S. Lee"],
                    "citation_count": 17,
                    "abstract": "The work models package dependency ecosystems as heterogeneous graphs to detect abnormal supply chain behavior.",
                    "reading_guide": "适合对比传统依赖扫描方法，关注数据集构建和消融实验。",
                    "doi_url": None,
                    "pdf_url": "https://example.org/papers/supply-chain-graph.pdf",
                    "tags": ["供应链安全", "图学习"],
                    "evidence_sources": [evidence("NDSS Symposium", "https://www.ndss-symposium.org/", "会议论文", "2026-03-30")],
                    "updated_at": "2026-04-12",
                    "favorited": False,
                    "in_reading_list": False,
                    "compared": False,
                },
            ],
            "patent": [
                {
                    "id": "patent-adversarial-traffic",
                    "title": "一种基于对抗样本增强的恶意流量识别方法",
                    "patent_no": "CN116845732B",
                    "status": "已授权",
                    "applicant": "北京邮电大学",
                    "direction": "AI 安全",
                    "legal_timeline": [
                        {"date": "2024-03-12", "status": "公开", "description": "发明专利申请公布"},
                        {"date": "2025-01-20", "status": "实质审查", "description": "进入实质审查阶段"},
                        {"date": "2026-02-18", "status": "已授权", "description": "授权公告"},
                    ],
                    "abstract": "通过对抗样本增强训练流量分类模型，提升恶意流量识别在扰动场景下的鲁棒性。",
                    "similarity_hint": "与异常检测和对抗训练方向相关，可作为专利布局参考。",
                    "evidence_sources": [evidence("国家知识产权局专利检索", "https://pss-system.cponline.cnipa.gov.cn/", "专利数据库", "2026-04-15")],
                    "updated_at": "2026-04-15",
                    "favorited": False,
                    "compared": False,
                },
                {
                    "id": "patent-zero-trust-ics",
                    "title": "面向工业控制系统的零信任访问控制系统",
                    "patent_no": "CN117236981A",
                    "status": "实质审查",
                    "applicant": "某网络安全联合实验室",
                    "direction": "工控安全",
                    "legal_timeline": [
                        {"date": "2025-08-02", "status": "公开", "description": "发明专利申请公布"},
                        {"date": "2026-01-11", "status": "实质审查", "description": "进入实质审查阶段"},
                    ],
                    "abstract": "围绕工业协议会话、设备身份和操作指令建立持续风险评估和动态授权机制。",
                    "similarity_hint": "与关基保护、零信任网关和工业协议解析方向相近。",
                    "evidence_sources": [evidence("国家知识产权局专利检索", "https://pss-system.cponline.cnipa.gov.cn/", "专利数据库", "2026-04-14")],
                    "updated_at": "2026-04-14",
                    "favorited": True,
                    "compared": True,
                },
            ],
            "lab": [
                {
                    "id": "lab-tsinghua-ai-security",
                    "name": "AI 安全开放课题",
                    "institution": "清华大学网络空间安全研究院",
                    "region": "北京",
                    "topics": ["大模型安全", "对齐评测", "数据治理"],
                    "mentor": "李老师",
                    "requirements": ["具备 Python 与深度学习基础", "能提交项目计划书和每月进展报告", "优先考虑有安全竞赛经历的团队"],
                    "deadline": "2026-05-20",
                    "contact": "ai-security@example.edu.cn",
                    "cooperation_cases": ["大模型越狱评测基准", "安全对齐数据集构建"],
                    "datasets_or_code_links": ["https://github.com/example/llm-safety-benchmark"],
                    "evidence_sources": [evidence("实验室开放课题公告", "https://example.edu.cn/labs/ai-security-open", "开放课题", "2026-04-11")],
                    "updated_at": "2026-04-17",
                    "favorited": True,
                    "subscribed": False,
                    "compared": False,
                },
                {
                    "id": "lab-iie-supply-chain",
                    "name": "软件供应链安全开放课题",
                    "institution": "中科院信息工程研究所",
                    "region": "北京",
                    "topics": ["供应链安全", "漏洞挖掘", "图学习"],
                    "mentor": "王老师",
                    "requirements": ["熟悉软件依赖生态", "有代码审计或漏洞挖掘经验", "可参与暑期集中研发"],
                    "deadline": "2026-06-05",
                    "contact": "supply-chain@example.ac.cn",
                    "cooperation_cases": ["开源生态依赖风险图谱", "包投毒检测原型"],
                    "datasets_or_code_links": ["https://github.com/example/supply-chain-risk"],
                    "evidence_sources": [evidence("开放课题征集通知", "https://example.ac.cn/open-topics/supply-chain", "开放课题", "2026-04-09")],
                    "updated_at": "2026-04-16",
                    "favorited": False,
                    "subscribed": True,
                    "compared": True,
                },
            ],
        }

    def list_items(self, item_type: ResearchItemType, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = [deepcopy(item) for item in self._items[item_type]]
        items = self._apply_filters(items, filters)
        return self._sort(items, filters.get("sort"))

    def get_item(self, item_type: ResearchItemType, item_id: str) -> dict[str, Any] | None:
        for item in self._items[item_type]:
            if item["id"] == item_id:
                return deepcopy(item)
        return None

    def toggle_flag(self, item_type: ResearchItemType, item_id: str, field: str) -> bool:
        for item in self._items[item_type]:
            if item["id"] == item_id:
                item[field] = not bool(item.get(field, False))
                return bool(item[field])
        raise KeyError(item_id)

    def compared_items(self) -> list[dict[str, Any]]:
        compared: list[dict[str, Any]] = []
        for item_type, items in self._items.items():
            for item in items:
                if item.get("compared"):
                    compared.append(self._to_compare_item(item_type, item))
        return compared

    def _apply_filters(self, items: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
        query = (filters.get("query") or "").strip().lower()
        direction = filters.get("direction")
        level = filters.get("level")
        source = filters.get("source")
        conference = filters.get("conference")
        deadline = filters.get("deadline")

        if query:
            items = [item for item in items if query in self._search_blob(item)]
        if direction and direction != "全部方向":
            items = [item for item in items if self._matches_direction(item, direction)]
        if level:
            items = [item for item in items if item.get("level") == level]
        if source:
            items = [item for item in items if source in str(item.get("source", ""))]
        if conference:
            items = [item for item in items if conference in str(item.get("venue", ""))]
        if deadline and deadline != "all":
            items = [item for item in items if self._within_deadline(item.get("deadline"), deadline)]
        return items

    def _sort(self, items: list[dict[str, Any]], sort: str | None) -> list[dict[str, Any]]:
        if sort == "deadline":
            return sorted(items, key=lambda item: self._deadline_key(item.get("deadline")))
        if sort == "updated":
            return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)
        if sort == "citation":
            return sorted(items, key=lambda item: item.get("citation_count", 0), reverse=True)
        if sort == "hot":
            return sorted(items, key=lambda item: item.get("growth", item.get("citation_count", 0)), reverse=True)
        return sorted(items, key=lambda item: item.get("match_score", 0), reverse=True)

    def _search_blob(self, item: dict[str, Any]) -> str:
        values: list[str] = []
        for value in item.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(v) for v in value)
        return " ".join(values).lower()

    def _matches_direction(self, item: dict[str, Any], direction: str) -> bool:
        values = [str(item.get("direction", "")), *[str(tag) for tag in item.get("tags", [])], *[str(topic) for topic in item.get("topics", [])]]
        return any(direction in value for value in values)

    def _within_deadline(self, raw_deadline: Any, deadline_filter: str) -> bool:
        if not isinstance(raw_deadline, str) or raw_deadline == "滚动申报":
            return deadline_filter in {"rolling", "upcoming"}
        try:
            deadline = datetime.strptime(raw_deadline, "%Y-%m-%d").date()
        except ValueError:
            return False
        today = date.today()
        if deadline_filter == "upcoming":
            return deadline >= today
        if deadline_filter == "30d":
            return today <= deadline <= today + timedelta(days=30)
        if deadline_filter == "90d":
            return today <= deadline <= today + timedelta(days=90)
        return True

    def _deadline_key(self, raw_deadline: Any) -> str:
        if raw_deadline == "滚动申报":
            return "9999-12-31"
        return str(raw_deadline or "9999-12-31")

    def _to_compare_item(self, item_type: str, item: dict[str, Any]) -> dict[str, Any]:
        title = item.get("title") or item.get("name")
        source = item.get("source") or item.get("institution") or item.get("applicant") or item.get("venue")
        deadline_or_year = str(item.get("deadline") or item.get("year") or item.get("status") or "-")
        if item_type == "paper":
            metric_label = "引用量"
            metric_value = str(item.get("citation_count", 0))
        elif item_type == "patent":
            metric_label = "法律状态"
            metric_value = str(item.get("status", "-"))
        else:
            metric_label = "匹配度"
            metric_value = f"{item.get('match_score', 0)}%" if "match_score" in item else "待评估"
        return {
            "item_type": item_type,
            "item_id": item["id"],
            "title": title,
            "source": source,
            "deadline_or_year": deadline_or_year,
            "metric_label": metric_label,
            "metric_value": metric_value,
            "recommendation_reason": item.get("recommendation_reason") or item.get("summary") or item.get("similarity_hint", ""),
        }


research_repository = ResearchRepository()
