// Status: real

export const HTTP_BASICS_VIDEO_PROMPT =
  'A smooth 10-second educational animation showing an HTTP request traveling from a browser through DNS resolution and a TCP/TLS handshake to a web server, then returning as a response. Clean ivory background, navy technical lines, blue request path, green response path, precise diagram style.';

const LEGACY_HTTP_BASICS_OMNI_PROMPT =
  `${HTTP_BASICS_VIDEO_PROMPT} No logos, watermarks, subtitles, captions, title cards, UI badges, or overlay text.`;

export const HTTP_BASICS_OMNI_GENERATION_PROMPT =
  [
    'Create a polished 10-second 16:9 educational motion-graphics video titled "一次 HTTPS 请求如何完成？" for Chinese university students.',
    'Use one stable, front-facing technical diagram with three clearly labeled nodes: "浏览器", "DNS 服务器", and "Web 服务器". Keep the camera fixed so every label remains readable.',
    'Use a clean ivory background, navy typography and technical lines, blue for the outgoing request, green for the returning response, and a restrained gold accent for TLS security. Animate small packet tokens, directional arrows, a certificate card, and a five-step progress timeline.',
    'Storyboard with exact on-screen Simplified Chinese text:',
    '0.0-1.0s: show the title "一次 HTTPS 请求如何完成？" and subtitle "从域名解析到加密响应".',
    '1.0-2.5s: highlight "① DNS 解析" and show "example.com → IP 地址" between the browser and DNS server.',
    '2.5-4.0s: highlight "② TCP 三次握手" and animate "SYN → SYN-ACK → ACK" between the browser and Web server.',
    '4.0-6.0s: highlight "③ TLS 安全连接" with the teaching note "证书验证 · 密钥协商 · 建立加密通道".',
    '6.0-8.0s: highlight "④ HTTP 请求" and show a blue request card reading "GET /index.html" and "Host: example.com".',
    '8.0-10.0s: animate a green return path labeled "⑤ HTTP 响应", show "200 OK · HTML", then finish with the takeaway "HTTPS = HTTP + TLS 加密" and the compact recap "DNS → TCP → TLS → Request → Response".',
    'Render only the specified instructional text in crisp, large, stable typography. Keep each step label visible long enough to read; do not morph, misspell, replace, or invent text.',
    'Use smooth purposeful transitions and layered editorial motion design, not a plain icon slideshow. No brand names, logos, watermarks, provider marks, decorative badges, unrelated captions, random characters, tiny text, photorealism, or dark cyberpunk styling.',
  ].join(' ');

export const HTTP_BASICS_LOCAL_VIDEO_PATH =
  '/assets/websec/generated/videos/http-basics.mp4';

export type LocalVideoPreset = {
  assetPath: string;
  kpId: string;
  dimensions: '1280x720';
  duration: 10;
  provider: 'google-omni-local';
  model: 'Google Omni';
};

const httpBasicsPreset: LocalVideoPreset = {
  assetPath: HTTP_BASICS_LOCAL_VIDEO_PATH,
  kpId: 'http-basics',
  dimensions: '1280x720',
  duration: 10,
  provider: 'google-omni-local',
  model: 'Google Omni',
};

const localPromptKeys = new Set([
  HTTP_BASICS_VIDEO_PROMPT,
  LEGACY_HTTP_BASICS_OMNI_PROMPT,
  HTTP_BASICS_OMNI_GENERATION_PROMPT,
].map(normalizeMediaPrompt));

/** Match only explicitly curated prompts; arbitrary prompts must keep the live path. */
export function resolveLocalVideoPreset(prompt: string): LocalVideoPreset | undefined {
  return localPromptKeys.has(normalizeMediaPrompt(prompt)) ? httpBasicsPreset : undefined;
}

function normalizeMediaPrompt(prompt: string): string {
  return prompt.trim().replace(/\s+/g, ' ');
}
