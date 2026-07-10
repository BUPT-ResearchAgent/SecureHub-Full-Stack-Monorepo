// Status: mock
//
// 4-B-3 evidence contract freeze (docs/api/evidence-contract.md v1)：
//   - `excerpt` → `chunk_text`
//   - 新增 required: `score`, `platform`, `rights_note`
//   - 新增 optional: `title`, `collection_mode`（提到顶层）, `license`
//   - 移除自由形态 `metadata` 兜底
//   - `source_url` 在 platform === 'manual' 时允许为 null
import type { EvidenceChunkDTO } from '@/lib/sse.types';

export const mockEvidenceChunks: EvidenceChunkDTO[] = [
  {
    chunk_id: '00000000-0000-0000-0000-000000000501',
    document_id: '00000000-0000-0000-0000-000000000601',
    chunk_text:
      'SQL 注入通常发生在未受信任输入被拼接进查询语句时，攻击者可能读取或篡改数据库内容。',
    excerpt: 'SQL 注入通常发生在未受信任输入被拼接进查询语句时，攻击者可能读取或篡改数据库内容。',
    score: 0.91,
    platform: 'owasp',
    rights_note: 'CC BY-SA 4.0',
    source_url: 'https://owasp.org/www-community/attacks/SQL_Injection',
    title: 'OWASP SQL Injection 攻击说明',
    author: 'OWASP',
    published_at: null,
    fetched_at: '2026-06-09T00:00:00Z',
    collection_mode: 'scrapling',
    asset_type: 'web_article',
    page_no: null,
    chapter: 'SQL 注入基础',
    timestamp: null,
    license: 'CC BY-SA 4.0',
    reliability: 0.92,
  },
  {
    chunk_id: '00000000-0000-0000-0000-000000000502',
    document_id: '00000000-0000-0000-0000-000000000602',
    chunk_text:
      '参数化查询会把用户输入作为数据绑定，避免输入内容被数据库解释为 SQL 语法片段。',
    excerpt: '参数化查询会把用户输入作为数据绑定，避免输入内容被数据库解释为 SQL 语法片段。',
    score: 0.87,
    platform: 'portswigger',
    rights_note: 'PortSwigger Academy 内容用于学习引用，保留原站链接',
    source_url: 'https://portswigger.net/web-security/sql-injection',
    title: 'PortSwigger Web Security Academy · SQL Injection',
    author: 'PortSwigger Web Security Academy',
    published_at: null,
    fetched_at: '2026-06-09T00:00:00Z',
    collection_mode: 'scrapling',
    asset_type: 'web_article',
    page_no: null,
    chapter: '防御与参数化查询',
    timestamp: null,
    license: null,
    reliability: 0.9,
  },
  {
    chunk_id: '00000000-0000-0000-0000-000000000503',
    document_id: '00000000-0000-0000-0000-000000000603',
    chunk_text:
      '演示环境中先判断注入点，再用报错、布尔或时间盲注确认查询结构，最后说明修复方式。',
    excerpt: '演示环境中先判断注入点，再用报错、布尔或时间盲注确认查询结构，最后说明修复方式。',
    score: 0.78,
    platform: 'bili',
    rights_note: '仅引用视频转写片段用于课堂演示，不搬运原视频',
    source_url: 'https://www.bilibili.com/video/BV1sql_demo',
    title: '网安教学演示 · SQL 注入实战',
    author: '网安教学演示账号',
    published_at: '2025-11-18T00:00:00Z',
    fetched_at: '2026-06-09T00:00:00Z',
    collection_mode: 'mediacrawler',
    asset_type: 'video_transcript',
    page_no: null,
    chapter: 'SQL 注入演示转写',
    timestamp: 183,
    license: null,
    reliability: 0.78,
  },
];
