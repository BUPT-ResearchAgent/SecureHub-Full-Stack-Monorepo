// Status: mock
// 学习效果预测：折线图（历史 + 预测段虚线 + 置信区间阴影）+ 加速建议。

import { useMemo } from 'react';
import { CalendarClock, Sparkles, Zap } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import type { LearningForecast as LearningForecastData } from '@/lib/types/assessment.types';

export type LearningForecastProps = {
  forecast: LearningForecastData;
};

const WIDTH = 560;
const HEIGHT = 200;
const PAD = 32;

export function LearningForecast({ forecast }: LearningForecastProps) {
  const all = [...forecast.historical, ...forecast.forecast];
  const xRange = all.length - 1;

  const xFor = (idx: number) => PAD + (idx / xRange) * (WIDTH - PAD * 2);
  const yFor = (value: number) => HEIGHT - PAD - value * (HEIGHT - PAD * 2);

  const historicalPath = useMemo(
    () => forecast.historical.map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${xFor(idx)} ${yFor(point.expected)}`).join(' '),
    [forecast.historical, xRange],
  );

  const forecastStartIdx = forecast.historical.length - 1;
  const forecastPath = useMemo(
    () =>
      [forecast.historical[forecastStartIdx], ...forecast.forecast]
        .map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${xFor(forecastStartIdx + idx)} ${yFor(point.expected)}`)
        .join(' '),
    [forecast, forecastStartIdx, xRange],
  );

  const bandPath = useMemo(() => {
    const upperPoints = forecast.forecast.map((point, idx) =>
      `${xFor(forecastStartIdx + idx + 1)} ${yFor(point.upper)}`,
    );
    const lowerPoints = forecast.forecast.map((point, idx) =>
      `${xFor(forecastStartIdx + idx + 1)} ${yFor(point.lower)}`,
    ).reverse();
    return `M ${xFor(forecastStartIdx)} ${yFor(forecast.historical[forecastStartIdx].expected)} L ${upperPoints.join(' L ')} L ${lowerPoints.join(' L ')} Z`;
  }, [forecast, forecastStartIdx, xRange]);

  return (
    <Card title="学习效果预测" subtitle={`目标：${forecast.dimensionLabel} → ${Math.round(forecast.targetMastery * 100)}%`}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="学习预测折线">
          {[0.2, 0.4, 0.6, 0.8, 1.0].map((ratio) => (
            <line
              key={ratio}
              x1={PAD}
              y1={yFor(ratio)}
              x2={WIDTH - PAD}
              y2={yFor(ratio)}
              stroke="#e2e8f0"
              strokeDasharray="3 3"
            />
          ))}
          <line
            x1={PAD}
            y1={yFor(forecast.targetMastery)}
            x2={WIDTH - PAD}
            y2={yFor(forecast.targetMastery)}
            stroke="#10b981"
            strokeDasharray="4 4"
          />
          <text x={WIDTH - PAD} y={yFor(forecast.targetMastery) - 4} textAnchor="end" style={{ fontSize: 10, fill: '#10b981' }}>
            目标 {Math.round(forecast.targetMastery * 100)}%
          </text>
          <path d={bandPath} fill="rgba(29,78,216,0.12)" stroke="none" />
          <path d={historicalPath} fill="none" stroke="#1d4ed8" strokeWidth={2} />
          <path d={forecastPath} fill="none" stroke="#1d4ed8" strokeWidth={2} strokeDasharray="5 4" />
          {forecast.historical.map((point, idx) => (
            <circle key={idx} cx={xFor(idx)} cy={yFor(point.expected)} r={3} fill="#1d4ed8" />
          ))}
          {forecast.forecast.map((point, idx) => (
            <circle
              key={`f-${idx}`}
              cx={xFor(forecastStartIdx + idx + 1)}
              cy={yFor(point.expected)}
              r={3}
              fill="white"
              stroke="#1d4ed8"
              strokeWidth={1.4}
            />
          ))}
          <line
            x1={xFor(forecastStartIdx)}
            y1={PAD}
            x2={xFor(forecastStartIdx)}
            y2={HEIGHT - PAD}
            stroke="#94a3b8"
            strokeDasharray="2 4"
          />
          <text x={xFor(forecastStartIdx) + 4} y={PAD + 12} style={{ fontSize: 10, fill: '#64748b' }}>
            今日
          </text>
        </svg>

        <div className="space-y-3">
          <div className="rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3">
            <p className="flex items-center gap-1 text-xs font-semibold text-brand-blue-700">
              <CalendarClock className="h-3 w-3" />
              预计达到目标
            </p>
            <p className="mt-1 text-2xl font-semibold text-brand-blue-700">
              {forecast.expectedDays}
              <span className="ml-1 text-sm font-normal text-brand-blue-600">天</span>
              <span className="ml-2 text-xs text-brand-blue-500">
                ± {Math.max(forecast.expectedDays - forecast.confidenceLowDays, forecast.confidenceHighDays - forecast.expectedDays)} 天
              </span>
            </p>
            <p className="mt-1 text-[11px] text-brand-blue-600/80">
              置信区间 {forecast.confidenceLowDays} ~ {forecast.confidenceHighDays} 天
            </p>
          </div>

          <div className="rounded-xl border border-amber-100 bg-amber-50 p-3">
            <p className="flex items-center gap-1 text-xs font-semibold text-amber-700">
              <Zap className="h-3 w-3" />
              加速建议
            </p>
            <p className="mt-1 text-sm text-amber-900">
              每天多投入 <span className="font-semibold">{forecast.acceleration.extraMinutesPerDay} 分钟</span>
              ，可缩短到 <span className="font-semibold">{forecast.expectedDays - forecast.acceleration.shavedDays} 天</span>。
            </p>
          </div>

          <Tag tone="blue">
            <Sparkles className="mr-1 h-3 w-3" />
            预测基于近 30 天能力曲线 + 资源使用节奏
          </Tag>
        </div>
      </div>
    </Card>
  );
}
