# Status: mock

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from urllib.parse import urljoin

router = APIRouter()


class PolicyItem(BaseModel):
    title: str
    url: str


class PolicyResponse(BaseModel):
    items: List[PolicyItem]


POLICY_ITEMS = [
    PolicyItem(
        title="国家互联网应急中心发布《网络安全威胁处置与信息通报工作规范》",
        url="https://www.cac.gov.cn/2025/04/",
    ),
    PolicyItem(
        title="网信办关于开展优化属地营商网络环境专项行动的公告",
        url="https://www.cac.gov.cn/2025/03/",
    ),
    PolicyItem(
        title="关于进一步加强数据跨境流动安全评估的通知",
        url="https://www.cac.gov.cn/2025/02/",
    ),
    PolicyItem(
        title="《网络数据安全管理条例》配套标准规范发布",
        url="https://www.cac.gov.cn/2025/01/",
    ),
    PolicyItem(
        title="工业互联网安全应急演练指南（试行）正式印发",
        url="https://www.cac.gov.cn/2024/12/",
    ),
    PolicyItem(
        title="个人信息保护合规审计管理办法出台", url="https://www.cac.gov.cn/2024/11/"
    ),
    PolicyItem(
        title="网络安全漏洞管理规定修订发布", url="https://www.cac.gov.cn/2024/10/"
    ),
    PolicyItem(
        title="关键信息基础设施安全保护条例实施细则",
        url="https://www.cac.gov.cn/2024/09/",
    ),
    PolicyItem(
        title="生成式人工智能服务管理暂行办法解读",
        url="https://www.cac.gov.cn/2024/08/",
    ),
    PolicyItem(
        title="网络安全产业高质量发展三年行动计划",
        url="https://www.cac.gov.cn/2024/07/",
    ),
]


@router.get("/policies", response_model=PolicyResponse)
def fetch_policies() -> PolicyResponse:
    return PolicyResponse(items=POLICY_ITEMS)
