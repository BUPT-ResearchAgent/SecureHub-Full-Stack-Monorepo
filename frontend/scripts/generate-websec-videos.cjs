/* Status: curated-demo
 *
 * Reproducible, silent WEBSEC-101 motion diagrams. These files are intentionally
 * labelled curated rather than model-generated in the product metadata.
 */

const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const OUTPUT_DIR = path.resolve(
  __dirname,
  '../public/assets/websec/generated/videos',
);
const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const videos = [
  {
    filename: 'http-request-lifecycle.mp4',
    title: 'HTTP 请求生命周期',
    eyebrow: '从浏览器到可信响应',
    lesson: '每一次请求，都要重新经过边界校验。',
    nodes: [
      { label: '浏览器', note: '构造请求', x: 70, y: 280, tone: 'blue' },
      { label: '请求边界', note: '协议与输入', x: 315, y: 190, tone: 'navy' },
      { label: '安全校验', note: '认证 · 校验', x: 560, y: 280, tone: 'green' },
      { label: '业务处理', note: '最小权限', x: 805, y: 190, tone: 'navy' },
      { label: '可信响应', note: '编码后输出', x: 1050, y: 280, tone: 'green' },
    ],
    edges: [
      { from: 0, to: 1, label: '请求行 / 头 / 体', tone: 'blue' },
      { from: 1, to: 2, label: '规范化', tone: 'blue' },
      { from: 2, to: 3, label: '已验证数据', tone: 'green' },
      { from: 3, to: 4, label: '状态码 / 响应体', tone: 'green' },
    ],
  },
  {
    filename: 'xss-defense-chain.mp4',
    title: 'XSS 分层防御链',
    eyebrow: '让不可信输入始终只是数据',
    lesson: '净化不是万能答案；输出编码必须匹配上下文。',
    nodes: [
      { label: '不可信输入', note: '<输入>', x: 70, y: 280, tone: 'red' },
      { label: '数据处理', note: '保留业务含义', x: 315, y: 190, tone: 'navy' },
      { label: '输出编码', note: '匹配上下文', x: 560, y: 280, tone: 'green' },
      { label: 'CSP', note: '限制脚本来源', x: 805, y: 190, tone: 'green' },
      { label: '文本呈现', note: '不被解释执行', x: 1050, y: 280, tone: 'green' },
    ],
    edges: [
      { from: 0, to: 1, label: '进入应用', tone: 'red' },
      { from: 1, to: 2, label: 'HTML / 属性 / 脚本', tone: 'blue' },
      { from: 2, to: 3, label: '纵深防御', tone: 'green' },
      { from: 3, to: 4, label: '安全输出', tone: 'green' },
    ],
    blocked: {
      from: 0,
      x: 525,
      y: 520,
      label: '直接写入危险接口',
    },
  },
  {
    filename: 'ssrf-egress-guard.mp4',
    title: 'SSRF 出站控制',
    eyebrow: '先验证目标，再允许服务端联网',
    lesson: '连接前再次解析与校验，阻断 DNS 重绑定。',
    nodes: [
      { label: '用户 URL', note: '不可信目标', x: 70, y: 280, tone: 'red' },
      { label: '协议 / 域名', note: '白名单', x: 315, y: 190, tone: 'blue' },
      { label: 'DNS 复核', note: '连接前校验', x: 560, y: 280, tone: 'green' },
      { label: '出站代理', note: '统一审计', x: 805, y: 190, tone: 'navy' },
      { label: '公网资源', note: '允许目标', x: 1050, y: 280, tone: 'green' },
    ],
    edges: [
      { from: 0, to: 1, label: '解析请求', tone: 'red' },
      { from: 1, to: 2, label: '地址段校验', tone: 'blue' },
      { from: 2, to: 3, label: '已批准目标', tone: 'green' },
      { from: 3, to: 4, label: '受控出站', tone: 'green' },
    ],
    blocked: {
      from: 0,
      x: 525,
      y: 520,
      label: '环回 / 内网 / 云元数据',
    },
  },
];

async function renderVideo(page, config) {
  return page.evaluate(async (video) => {
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 720;
    document.body.replaceChildren(canvas);
    document.body.style.margin = '0';
    document.body.style.background = '#f7f3e9';
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas 2D unavailable');

    const palette = {
      background: '#f7f3e9',
      navy: '#0b2a52',
      blue: '#176b87',
      green: '#25805f',
      red: '#c2413b',
      muted: '#6b7280',
      line: '#d7d9d2',
      white: '#fffdf8',
    };
    const colorFor = (tone) => palette[tone] || palette.navy;
    const roundedRect = (x, y, width, height, radius) => {
      context.beginPath();
      context.roundRect(x, y, width, height, radius);
    };
    const nodeCenter = (node) => ({ x: node.x + 80, y: node.y + 60 });

    function drawArrow(from, to, color, progress, label) {
      const start = nodeCenter(from);
      const end = nodeCenter(to);
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const length = Math.hypot(dx, dy);
      const ux = dx / length;
      const uy = dy / length;
      const startX = start.x + ux * 86;
      const startY = start.y + uy * 64;
      const endX = end.x - ux * 86;
      const endY = end.y - uy * 64;
      const visibleX = startX + (endX - startX) * progress;
      const visibleY = startY + (endY - startY) * progress;
      context.strokeStyle = color;
      context.lineWidth = 5;
      context.lineCap = 'round';
      context.beginPath();
      context.moveTo(startX, startY);
      context.lineTo(visibleX, visibleY);
      context.stroke();
      if (progress > 0.95) {
        const angle = Math.atan2(endY - startY, endX - startX);
        context.fillStyle = color;
        context.beginPath();
        context.moveTo(endX, endY);
        context.lineTo(endX - 16 * Math.cos(angle - Math.PI / 6), endY - 16 * Math.sin(angle - Math.PI / 6));
        context.lineTo(endX - 16 * Math.cos(angle + Math.PI / 6), endY - 16 * Math.sin(angle + Math.PI / 6));
        context.closePath();
        context.fill();
      }
      if (progress > 0.45) {
        context.font = '600 16px "Microsoft YaHei", sans-serif';
        context.fillStyle = color;
        context.textAlign = 'center';
        context.fillText(label, (startX + endX) / 2, (startY + endY) / 2 - 18);
      }
      if (progress > 0.05 && progress < 0.98) {
        const pulse = (progress * 1.35) % 1;
        context.fillStyle = color;
        context.beginPath();
        context.arc(
          startX + (endX - startX) * pulse,
          startY + (endY - startY) * pulse,
          8,
          0,
          Math.PI * 2,
        );
        context.fill();
      }
    }

    function drawNode(node, reveal, active) {
      const color = colorFor(node.tone);
      context.save();
      context.globalAlpha = reveal;
      context.shadowColor = active ? `${color}55` : 'transparent';
      context.shadowBlur = active ? 22 : 0;
      roundedRect(node.x, node.y, 160, 120, 14);
      context.fillStyle = palette.white;
      context.fill();
      context.lineWidth = active ? 4 : 2;
      context.strokeStyle = color;
      context.stroke();
      context.shadowBlur = 0;
      context.fillStyle = color;
      context.fillRect(node.x, node.y, 160, 8);
      context.font = '700 23px "Microsoft YaHei", sans-serif';
      context.textAlign = 'center';
      context.fillStyle = palette.navy;
      context.fillText(node.label, node.x + 80, node.y + 56);
      context.font = '500 16px "Microsoft YaHei", sans-serif';
      context.fillStyle = palette.muted;
      context.fillText(node.note, node.x + 80, node.y + 88);
      context.restore();
    }

    function drawFrame(elapsed) {
      const duration = 6200;
      const normalized = Math.min(elapsed / duration, 1);
      context.fillStyle = palette.background;
      context.fillRect(0, 0, canvas.width, canvas.height);

      context.strokeStyle = '#e4e2db';
      context.lineWidth = 1;
      for (let x = 40; x < canvas.width; x += 40) {
        context.beginPath();
        context.moveTo(x, 0);
        context.lineTo(x, canvas.height);
        context.stroke();
      }
      for (let y = 40; y < canvas.height; y += 40) {
        context.beginPath();
        context.moveTo(0, y);
        context.lineTo(canvas.width, y);
        context.stroke();
      }
      context.fillStyle = palette.background;
      context.fillRect(30, 20, 1220, 670);

      context.font = '700 44px "Microsoft YaHei", sans-serif';
      context.textAlign = 'left';
      context.fillStyle = palette.navy;
      context.fillText(video.title, 70, 82);
      context.font = '500 18px "Microsoft YaHei", sans-serif';
      context.fillStyle = palette.muted;
      context.fillText(video.eyebrow, 72, 116);

      roundedRect(1015, 54, 195, 38, 19);
      context.fillStyle = palette.navy;
      context.fill();
      context.font = '600 15px "Microsoft YaHei", sans-serif';
      context.textAlign = 'center';
      context.fillStyle = palette.white;
      context.fillText('SECUREHUB · 精选动画', 1112, 79);

      video.edges.forEach((edge, index) => {
        const start = 0.08 + index * 0.17;
        const edgeProgress = Math.max(0, Math.min((normalized - start) / 0.18, 1));
        drawArrow(
          video.nodes[edge.from],
          video.nodes[edge.to],
          colorFor(edge.tone),
          edgeProgress,
          edge.label,
        );
      });
      video.nodes.forEach((node, index) => {
        const reveal = Math.max(0, Math.min((normalized - index * 0.12) / 0.1, 1));
        const activeIndex = Math.min(
          video.nodes.length - 1,
          Math.floor(normalized * video.nodes.length),
        );
        drawNode(node, reveal, activeIndex === index);
      });

      if (video.blocked && normalized > 0.42) {
        const reveal = Math.min((normalized - 0.42) / 0.18, 1);
        const source = nodeCenter(video.nodes[video.blocked.from]);
        context.save();
        context.globalAlpha = reveal;
        context.strokeStyle = palette.red;
        context.setLineDash([10, 8]);
        context.lineWidth = 4;
        context.beginPath();
        context.moveTo(source.x + 45, source.y + 48);
        context.quadraticCurveTo(285, 560, video.blocked.x, video.blocked.y);
        context.stroke();
        context.setLineDash([]);
        context.font = '700 28px "Microsoft YaHei", sans-serif';
        context.textAlign = 'center';
        context.fillStyle = palette.red;
        context.fillText('×', video.blocked.x, video.blocked.y + 8);
        context.font = '600 17px "Microsoft YaHei", sans-serif';
        context.fillText(video.blocked.label, video.blocked.x, video.blocked.y + 42);
        context.restore();
      }

      roundedRect(70, 625, 1140, 52, 10);
      context.fillStyle = palette.white;
      context.fill();
      context.strokeStyle = palette.line;
      context.lineWidth = 2;
      context.stroke();
      context.font = '700 20px "Microsoft YaHei", sans-serif';
      context.textAlign = 'center';
      context.fillStyle = palette.navy;
      context.fillText(video.lesson, 640, 658);
    }

    const stream = canvas.captureStream(30);
    const mimeType = [
      'video/mp4;codecs=avc1.42001E',
      'video/mp4',
      'video/webm;codecs=vp9',
      'video/webm;codecs=vp8',
      'video/webm',
    ].find((candidate) => MediaRecorder.isTypeSupported(candidate));
    if (!mimeType) throw new Error('No supported MediaRecorder video codec');
    const recorder = new MediaRecorder(stream, {
      mimeType,
      videoBitsPerSecond: 2_800_000,
    });
    const chunks = [];
    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size) chunks.push(event.data);
    });
    const stopped = new Promise((resolve) => recorder.addEventListener('stop', resolve, { once: true }));
    recorder.start(250);
    const startedAt = performance.now();
    await new Promise((resolve) => {
      function animate(now) {
        const elapsed = now - startedAt;
        drawFrame(elapsed);
        if (elapsed < 6200) {
          requestAnimationFrame(animate);
        } else {
          resolve();
        }
      }
      requestAnimationFrame(animate);
    });
    recorder.stop();
    await stopped;
    stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(chunks, { type: mimeType });
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    return {
      base64: btoa(binary),
      mimeType,
      size: bytes.length,
    };
  }, config);
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const browser = await chromium.launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--disable-background-timer-throttling'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    for (const video of videos) {
      const result = await renderVideo(page, video);
      if (result.size < 10_000) {
        throw new Error(`${video.filename} was unexpectedly small (${result.size} bytes)`);
      }
      const target = path.join(OUTPUT_DIR, video.filename);
      fs.writeFileSync(target, Buffer.from(result.base64, 'base64'));
      process.stdout.write(`${video.filename}\t${result.size}\t${result.mimeType}\n`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
