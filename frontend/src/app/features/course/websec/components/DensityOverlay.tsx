// Status: real

import { useEffect, useRef, useState } from 'react';
import type { Viewport } from 'reactflow';

export type DensityNode = {
  id: string;
  x: number;
  y: number;
  radius: number;
  color: string;
};

export function DensityOverlay({
  nodes,
  viewport,
}: {
  nodes: readonly DensityNode[];
  viewport: Viewport;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [size, setSize] = useState({ width: 1, height: 1 });
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      setSize({
        width: Math.max(1, Math.round(entry.contentRect.width)),
        height: Math.max(1, Math.round(entry.contentRect.height)),
      });
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const update = () => setDark(root.classList.contains('dark'));
    update();
    const observer = new MutationObserver(update);
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const frame = window.requestAnimationFrame(() => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(size.width * ratio);
      canvas.height = Math.round(size.height * ratio);
      const context = canvas.getContext('2d');
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, size.width, size.height);
      context.globalCompositeOperation = dark ? 'screen' : 'multiply';

      nodes.forEach((node) => {
        const x = viewport.x + node.x * viewport.zoom;
        const y = viewport.y + node.y * viewport.zoom;
        const radius = Math.max(62, node.radius * viewport.zoom * 2.1);
        if (
          x + radius < 0
          || y + radius < 0
          || x - radius > size.width
          || y - radius > size.height
        ) return;
        const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
        gradient.addColorStop(0, withAlpha(node.color, dark ? 0.2 : 0.16));
        gradient.addColorStop(0.42, withAlpha(node.color, dark ? 0.1 : 0.075));
        gradient.addColorStop(1, withAlpha(node.color, 0));
        context.fillStyle = gradient;
        context.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      });
      context.globalCompositeOperation = 'source-over';
    });
    return () => window.cancelAnimationFrame(frame);
  }, [dark, nodes, size.height, size.width, viewport]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 z-0 h-full w-full blur-[10px]"
      aria-hidden
    />
  );
}

function withAlpha(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  const value = normalized.length === 3
    ? normalized.split('').map((part) => `${part}${part}`).join('')
    : normalized;
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}
