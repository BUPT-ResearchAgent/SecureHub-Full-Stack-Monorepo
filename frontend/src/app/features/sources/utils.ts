// Status: real
import {
  BadgeCheck,
  BookOpen,
  Bug,
  Code2,
  FileText,
  Globe2,
  MessageCircle,
  Radio,
  ShieldCheck,
  Video,
  type LucideIcon,
} from 'lucide-react';

const platformLabels: Record<string, string> = {
  owasp: 'OWASP',
  portswigger: 'PortSwigger',
  github: 'GitHub',
  csdn: 'CSDN',
  bili: 'B 站',
  bilibili: 'B 站',
  zhihu: '知乎',
  xhs: '小红书',
  wechat: '微信公众号',
  weixin: '微信公众号',
  cve: 'CVE',
  ctftime: 'CTFtime',
  securehub: '安枢智梯',
};

const platformIcons: Record<string, LucideIcon> = {
  owasp: ShieldCheck,
  portswigger: Bug,
  github: Code2,
  csdn: FileText,
  bili: Video,
  bilibili: Video,
  zhihu: MessageCircle,
  xhs: BookOpen,
  wechat: Radio,
  weixin: Radio,
  cve: BadgeCheck,
  ctftime: Globe2,
  securehub: ShieldCheck,
};

export function platformLabel(platform?: string | null): string {
  if (!platform) return '未知来源';
  return platformLabels[platform.toLowerCase()] ?? platform;
}

export function platformIcon(platform?: string | null): LucideIcon {
  if (!platform) return Globe2;
  return platformIcons[platform.toLowerCase()] ?? Globe2;
}
