import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

const MONO = '"IBM Plex Mono", "Courier New", monospace';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const val = payload[0].value;
  const color = val >= 0 ? 'var(--green)' : 'var(--red)';
  return (
    <div style={{
      background: 'var(--panel-alt)',
      border: '1px solid var(--border-hi)',
      padding: '8px 12px',
      fontFamily: MONO,
    }}>
      <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--cream-mid)', marginBottom: 4 }}>
        {new Date(label).toLocaleDateString([], { month: 'short', day: 'numeric' })}
      </div>
      <div style={{ fontSize: 14, color, fontFamily: '"Share Tech Mono", monospace' }}>
        {val >= 0 ? '+' : ''}${val.toFixed(2)}
      </div>
    </div>
  );
}

function PerformanceChart({ data }) {
  const safeData = (data || []).filter(
    d => d && typeof d.cumulative_pnl === 'number' && isFinite(d.cumulative_pnl)
  );

  if (safeData.length === 0) {
    return (
      <div style={{
        height: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: MONO,
        fontSize: 12,
        color: 'var(--cream-dim)',
        letterSpacing: '0.12em',
      }}>
        NO DATA — RUNS AFTER MARKET CLOSE
      </div>
    );
  }

  const isPositive = safeData[safeData.length - 1]?.cumulative_pnl >= 0;
  const stroke = isPositive ? 'var(--green)' : 'var(--red)';
  const gradId  = isPositive ? 'gradGreen' : 'gradRed';
  const stopColor = isPositive ? '#00cc6a' : '#ff2d55';

  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={safeData} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={stopColor} stopOpacity={0.22} />
            <stop offset="100%" stopColor={stopColor} stopOpacity={0.01} />
          </linearGradient>
        </defs>

        <CartesianGrid
          strokeDasharray="0"
          stroke="var(--border-hi)"
          vertical={false}
          horizontal={true}
        />

        <XAxis
          dataKey="date"
          stroke="var(--border-glow)"
          tick={{ fontSize: 9, fontFamily: MONO, fill: 'var(--cream-mid)', letterSpacing: '0.05em' }}
          tickFormatter={(d) => new Date(d).toLocaleDateString([], { month: 'short', day: 'numeric' })}
          tickLine={false}
          axisLine={false}
          tickMargin={6}
        />

        <YAxis
          stroke="var(--border-glow)"
          tick={{ fontSize: 9, fontFamily: MONO, fill: 'var(--cream-mid)' }}
          tickFormatter={(v) => `${v >= 0 ? '+' : ''}$${v.toFixed(0)}`}
          tickLine={false}
          axisLine={false}
          width={55}
        />

        <Tooltip content={<CustomTooltip />} />

        <ReferenceLine y={0} stroke="var(--border-glow)" strokeDasharray="4 4" />

        <Area
          type="monotone"
          dataKey="cumulative_pnl"
          stroke={stroke}
          strokeWidth={1.5}
          fill={`url(#${gradId})`}
          dot={false}
          activeDot={{ r: 3, fill: stroke, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default PerformanceChart;
