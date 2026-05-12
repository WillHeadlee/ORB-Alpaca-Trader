import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

function PerformanceChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400">No performance data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="date"
          stroke="#9CA3AF"
          tickFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <YAxis stroke="#9CA3AF" />
        <Tooltip
          contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
          labelStyle={{ color: '#9CA3AF' }}
          formatter={(value) => [`$${value.toFixed(2)}`, 'P&L']}
          labelFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
        <Line
          type="monotone"
          dataKey="cumulative_pnl"
          stroke="#10B981"
          strokeWidth={2}
          dot={false}
          name="Cumulative P&L"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default PerformanceChart;
