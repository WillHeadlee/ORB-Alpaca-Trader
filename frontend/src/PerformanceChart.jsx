import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

function PerformanceChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <p className="text-center text-zinc-600 text-sm font-mono py-8">No data yet</p>
    );
  }

  const min = Math.min(...data.map(d => d.cumulative_pnl));
  const isPositive = data[data.length - 1]?.cumulative_pnl >= 0;
  const stroke = isPositive ? '#34d399' : '#f87171';
  const fill = isPositive ? '#064e3b' : '#450a0a';

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={stroke} stopOpacity={0.2} />
            <stop offset="95%" stopColor={stroke} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="#52525b"
          tick={{ fontSize: 10, fontFamily: 'monospace' }}
          tickFormatter={(d) => new Date(d).toLocaleDateString([], { month: 'short', day: 'numeric' })}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#52525b"
          tick={{ fontSize: 10, fontFamily: 'monospace' }}
          tickFormatter={(v) => `$${v >= 0 ? '+' : ''}${v.toFixed(0)}`}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #3f3f46',
            borderRadius: '4px',
            fontSize: '12px',
            fontFamily: 'monospace',
          }}
          labelStyle={{ color: '#71717a' }}
          formatter={(v) => [`${v >= 0 ? '+' : ''}$${v.toFixed(2)}`, 'Cumulative']}
          labelFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <ReferenceLine y={0} stroke="#3f3f46" strokeDasharray="3 3" />
        <Area
          type="monotone"
          dataKey="cumulative_pnl"
          stroke={stroke}
          strokeWidth={1.5}
          fill="url(#pnlGrad)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default PerformanceChart;
