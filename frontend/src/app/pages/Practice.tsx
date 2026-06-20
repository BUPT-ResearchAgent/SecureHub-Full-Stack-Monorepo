import { BookOpen, Wrench, Trophy, Shield, Target, FileSearch, Clock, ExternalLink, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PageShell, Card, Tag } from '../components/PageShell';

interface CTFEvent {
  id: number;
  title: string;
  url: string;
  start: string;
  finish: string;
  format: string;
  participants: number;
  weight: number;
  description: string;
}

const loadCTFEvents = async (): Promise<CTFEvent[]> => {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/v1/ctftime?limit=15');
    const data = await res.json();
    return data;
  } catch (e) {
    console.error('Failed to load CTF events:', e);
    return [];
  }
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
};

const getStatus = (start: string, finish: string) => {
  const now = new Date();
  const startD = new Date(start);
  const finishD = new Date(finish);
  if (now < startD) return '即将';
  if (now <= finishD) return '进行中';
  return '已结束';
};

const CTFEvents = () => {
  const [events, setEvents] = useState<CTFEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCTFEvents().then((data) => {
      setEvents(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-brand-blue-600" />
        <span className="ml-2 text-sm text-slate-500">加载 CTFtime 赛事数据...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        {events.slice(0, 9).map((e) => (
          <Card key={e.id} href={e.url || `https://ctftime.org/event/${e.id}/`}>
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 bg-brand-blue-50 text-brand-blue-600 rounded-lg flex items-center justify-center shrink-0">
                <Trophy className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-900 truncate">{e.title}</p>
                  <Tag tone={getStatus(e.start, e.finish) === '进行中' ? 'green' : getStatus(e.start, e.finish) === '即将' ? 'blue' : 'default'}>
                    {getStatus(e.start, e.finish)}
                  </Tag>
                </div>
                <p className="text-xs text-slate-500 mt-1 truncate">{e.format} · {e.participants} 人参与</p>
                <p className="text-xs text-slate-400 mt-1">{formatDate(e.start)} - {formatDate(e.finish)}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
      <Card title="我的参赛时间线">
        <ol className="relative border-l border-slate-200 ml-2 space-y-4">
          {[
            { t: '校赛报名 · 强网杯', d: '2026-04-28' },
            { t: '校赛初赛 · 信安赛', d: '2026-05-15' },
            { t: '省赛决赛 · 挑战杯', d: '2026-06-20' },
          ].map((s) => (
            <li key={s.t} className="ml-4">
              <span className="absolute -left-1.5 w-3 h-3 bg-brand-blue-600 rounded-full" />
              <p className="text-sm text-slate-800">{s.t}</p>
              <p className="text-xs text-slate-500">{s.d}</p>
            </li>
          ))}
        </ol>
      </Card>
      <div className="text-center">
        <a href="https://ctftime.org/" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-sm text-brand-blue-600 hover:underline">
          <ExternalLink className="w-3 h-3 mr-1" />
          查看更多赛事 (CTFtime)
        </a>
      </div>
    </div>
  );
};

const Grid = ({
  items,
}: {
  items: { t: string; s: string; m?: string; tag?: string; icon?: any; href?: string }[];
}) => (
  <div className="grid grid-cols-3 gap-4">
    {items.map((x) => (
      <Card key={x.t} href={x.href}>
        <div className="flex items-start gap-3">
          {x.icon && (
            <div className="w-9 h-9 bg-brand-blue-50 text-brand-blue-600 rounded-lg flex items-center justify-center shrink-0">
              <x.icon className="w-4 h-4" />
            </div>
          )}
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-900">{x.t}</p>
              {x.tag && <Tag tone="blue">{x.tag}</Tag>}
            </div>
            <p className="text-xs text-slate-500 mt-1">{x.s}</p>
            {x.m && <p className="text-xs text-slate-400 mt-2">{x.m}</p>}
          </div>
        </div>
      </Card>
    ))}
  </div>
);

export function Practice() {
  const [params] = useSearchParams();
  const fromCourseSqli = params.get('from') === 'course-sqli';

  return (
    <div className="space-y-4">
      {fromCourseSqli && (
        <div className="rounded-xl border border-brand-blue-100 bg-brand-blue-50/70 px-4 py-3 text-sm text-brand-blue-800">
          同一画像驱动的延展示范：这里复用 SQL 注入学习结果，演示 Competition / Practice 入口；不新增真实竞赛 API。
        </div>
      )}
      <PageShell
        title="实战进阶"
        subtitle="教程、工具、竞赛与靶场 · 行动导向的实战能力建设"
        actions={<button className="px-3 py-1.5 text-sm bg-brand-blue-600 text-white rounded-lg">我要参赛</button>}
        tabs={[
        {
          key: 'tutorial',
          label: '教程中心',
          description: '分方向、分难度的网络安全实战教程，覆盖 Web、逆向、内网渗透、AI 安全等核心路径',
          render: () => (
            <Grid
              items={[
                { icon: BookOpen, t: 'Web 安全入门到进阶', s: '12 章节 · 覆盖 OWASP Top10', tag: '热门', href: 'https://portswigger.com/web-security' },
                { icon: BookOpen, t: '二进制漏洞挖掘实战', s: '8 章节 · Pwn 体系路径', href: 'https://ctf-wiki.org/pwn/linux/user-mode/environment/' },
                { icon: BookOpen, t: '内网渗透实操', s: '10 章节 · 域渗透全流程', href: 'https://orange-cyberdefense.github.io/orangewalk/' },
                { icon: BookOpen, t: '代码审计与白盒方法', s: 'Java / PHP 审计', href: 'https://programmer.group/' },
                { icon: BookOpen, t: '蓝队应急响应', s: '日志分析与溯源', href: 'https://incident-response.com/' },
                { icon: BookOpen, t: 'AI 安全对抗基础', s: '模型攻防与对齐', href: 'https://github.com/DeepSpaceHarbor/Awesome-AI-Security' },
                { icon: BookOpen, t: 'Awesome Web Security', s: 'Web 安全资源集', href: 'https://github.com/qazbnm456/awesome-web-security' },
                { icon: BookOpen, t: 'Awesome Security', s: '安全资源大全', href: 'https://github.com/sbilly/awesome-security' },
                { icon: BookOpen, t: 'Cyber Security University', s: '实战学习路径', href: 'https://github.com/brootware/awesome-cyber-security-university' },
              ]}
            />
          ),
        },
        {
          key: 'tools',
          label: '工具库',
          description: '渗透测试、安全分析与防御工程常用工具集合，附配置模板与使用说明',
          render: () => (
            <Grid
              items={[
                { icon: Wrench, t: 'Burp Suite 配置模板', s: '面向电商逻辑漏洞', href: 'https://portswigger.com/burp' },
                { icon: Wrench, t: 'Nmap 高阶脚本集', s: '内网发现与服务指纹', href: 'https://nmap.org/' },
                { icon: Wrench, t: 'Cobalt Strike 教研版', s: '红队教学专用', href: 'https://www.cobaltstrike.com/' },
                { icon: Wrench, t: 'CyberChef 工作流', s: '30+ 常用流水线', href: 'https://gchq.github.io/CyberChef/' },
                { icon: Wrench, t: 'Sliver C2 实验包', s: '合法教学使用', href: 'https://github.com/BishopFox/sliver' },
                { icon: Wrench, t: '取证工具箱', s: 'Volatility · Autopsy', href: 'https://www.volatilityfoundation.org/' },
                { icon: Wrench, t: 'Pwntools', s: 'CTF pwn 框架', href: 'https://github.com/Gallopsled/pwntools' },
                { icon: Wrench, t: 'Ghidra', s: '逆向分析工具', href: 'https://ghidra-sre.org/' },
                { icon: Wrench, t: 'Metasploit', s: '渗透测试框架', href: 'https://www.metasploit.com/' },
                { icon: Wrench, t: 'SQLMap', s: 'SQL 注入工具', href: 'https://sqlmap.org/' },
                { icon: Wrench, t: 'Hashcat', s: '密码破解', href: 'https://hashcat.net/hashcat/' },
                { icon: Wrench, t: 'Wireshark', s: '网络分析', href: 'https://www.wireshark.org/' },
              ]}
            />
          ),
        },
        {
          key: 'contest',
          label: '竞赛专区',
          description: '当前开放的安全赛事信息、历届优秀作品参考与个人参赛时间线管理',
          render: () => <CTFEvents />,
        },
        {
          key: 'hvv',
          label: '护网行动',
          description: '护网行动预告、红蓝队典型战法复盘与参与指引，了解实战演练全貌',
          render: () => (
            <Grid
              items={[
                { icon: Shield, t: '护网行动预告', s: '7 月启动 · 报名通道', tag: '预告', href: 'https://www.gov.cn/' },
                { icon: Shield, t: '红队典型战法复盘', s: '近三年 58 起案例', href: 'http://www.redteam-wiki.org/' },
                { icon: Shield, t: '蓝队监测与值守手册', s: 'SOP 与排班模板', href: 'https://www.cisa.gov/' },
                { icon: Shield, t: '攻防演练态势看板', s: '实时攻击源分布', href: 'https://www.elastic.co/' },
              ]}
            />
          ),
        },
        {
          key: 'range',
          label: '靶场演练',
          description: '在线靶场环境快速接入，涵盖 Web、内网、工控、AI 对抗等多类型挑战',
          render: () => (
            <Grid
              items={[
                { icon: Target, t: 'Hack The Box', s: '在线靶场 · 每周更新', tag: '在线', href: 'https://www.hackthebox.eu/' },
                { icon: Target, t: 'TryHackMe', s: '入门友好 · 学习路径', tag: '在线', href: 'https://tryhackme.com/' },
                { icon: Target, t: 'PortSwigger Lab', s: 'Web 安全实验室', tag: '在线', href: 'https://portswigger.com/web-security/academy' },
                { icon: Target, t: 'Pwnable.kr', s: 'Pwn 题目集', tag: '在线', href: 'https://pwnable.kr/' },
                { icon: Target, t: 'OverTheWire', s: 'Wargame 练习', tag: '在线', href: 'https://overthewire.org/wargames/' },
                { icon: Target, t: 'VulnHub', s: '漏洞虚拟机', tag: '在线', href: 'https://www.vulnhub.com/' },
                { icon: Target, t: 'CryptoHack', s: '密码学挑战', tag: '在线', href: 'https://cryptohack.org/' },
                { icon: Target, t: 'Root-Me', s: '综合靶场', tag: '在线', href: 'https://www.root-me.org/' },
                { icon: Target, t: 'PentesterLab', s: '渗透练习', tag: '在线', href: 'https://pentesterlab.com/' },
              ]}
            />
          ),
        },
        {
          key: 'cases',
          label: '实战案例',
          description: '真实攻防场景的结构化分析与复盘报告，提炼可复用的攻防经验',
          render: () => (
            <Card>
              <ul className="divide-y divide-slate-100">
                {[
                  { t: '某高校 VPN 接口未授权访问修复', tag: '企业实战', m: '2026-04', href: 'https://www.venustech.com.cn/new_type/aqtg/20230911/26223.html' },
                  { t: 'Log4shell漏洞研究及其挖矿案例分析', tag: '应急响应', m: '2026-03', href: 'https://www.anquanke.com/post/id/263217' },
                  { t: '电商风险之刷单浅析', tag: '业务安全', m: '2026-02', href: 'https://www.anquanke.com/post/id/224331' },
                  { t: 'IoT安全透视：D-Link DWR-932B固件全面逆向分析', tag: '硬件逆向', m: '2026-01', href: 'https://zhuanlan.zhihu.com/p/1898075424287854702' },
                ].map((x) => (
                  <li key={x.t}>
                    <a href={x.href} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-5 px-5 transition-colors">
                      <div className="flex items-center gap-3">
                        <FileSearch className="w-4 h-4 text-slate-400" />
                        <p className="text-sm text-slate-800">{x.t}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Tag>{x.tag}</Tag>
                        <span className="text-xs text-slate-400">{x.m}</span>
                      </div>
                    </a>
                  </li>
                ))}
              </ul>
            </Card>
          ),
        },
        {
          key: 'ddl',
          label: '竞赛DDL',
          description: '主流安全赛事的报名与提交截止日历，按紧急程度排序，不错过任何窗口',
          render: () => (
            <Card title="按紧急程度排序">
              <ul className="space-y-3">
                {[
                  { t: '强网杯青少年专项赛 · 初赛报名', d: '2026-04-30', days: 7, tone: 'red' as const },
                  { t: '全国大学生信息安全竞赛 · 作品提交', d: '2026-05-15', days: 22, tone: 'red' as const },
                  { t: 'AI 安全挑战赛 · 队伍确认', d: '2026-05-22', days: 29, tone: 'amber' as const },
                  { t: '工控安全邀请赛', d: '2026-06-18', days: 56, tone: 'amber' as const },
                  { t: '护网行动招募截止', d: '2026-07-05', days: 73, tone: 'default' as const },
                ].map((d) => (
                  <li
                    key={d.t}
                    className="flex items-center justify-between p-3 border border-slate-100 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <div>
                        <p className="text-sm text-slate-800">{d.t}</p>
                        <p className="text-xs text-slate-500">截止 {d.d}</p>
                      </div>
                    </div>
                    <Tag tone={d.tone}>{d.days} 天</Tag>
                  </li>
                ))}
              </ul>
            </Card>
          ),
        },
        ]}
      />
    </div>
  );
}
