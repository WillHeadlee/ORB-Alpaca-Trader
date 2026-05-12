import React, { useState, useEffect } from 'react';
import PerformanceChart from './PerformanceChart';
import KillSwitch from './KillSwitch';
import api from './api';

function Dashboard({ onLogout }) {
  const [status, setStatus] = useState(null);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [screener, setScreener] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [statusData, tradesData, perfData, screenerData] = await Promise.all([
        api.getStatus(),
        api.getTrades(20, 0),
        api.getPerformance('30d'),
        api.getScreenerResults(),
      ]);
      setStatus(statusData);
      setTrades(tradesData.trades);
      setPerformance(perfData);
      setScreener(screenerData.results);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <p className="text-white text-xl">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">ORB Trader</h1>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded ${status?.bot_status === 'running' ? 'bg-green-600' : 'bg-red-600'}`}>
            {status?.bot_status?.toUpperCase()}
          </span>
          <span className="px-3 py-1 bg-blue-600 rounded">
            MODE: {status?.mode?.toUpperCase()}
          </span>
          <button onClick={onLogout} className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600">
            Logout
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-gray-400 text-sm">Today P&L</p>
          <p className={`text-2xl font-bold ${(status?.today_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            ${status?.today_pnl?.toFixed(2) ?? '0.00'}
          </p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-gray-400 text-sm">Account Balance</p>
          <p className="text-2xl font-bold">${status?.account_balance?.toFixed(2) ?? '0.00'}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-gray-400 text-sm">Win Rate</p>
          <p className="text-2xl font-bold">{((performance?.win_rate ?? 0) * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-gray-400 text-sm">Total P&L (30d)</p>
          <p className={`text-2xl font-bold ${(performance?.total_pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            ${performance?.total_pnl?.toFixed(2) ?? '0.00'}
          </p>
        </div>
      </div>

      {/* Kill Switch */}
      <KillSwitch positions={status?.positions ?? []} onKill={loadData} />

      {/* Active Positions */}
      <div className="bg-gray-800 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-bold mb-4">Active Positions ({status?.positions?.length ?? 0})</h2>
        {status?.positions?.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-2">Symbol</th>
                <th className="pb-2">Quantity</th>
                <th className="pb-2">Entry Price</th>
                <th className="pb-2">Current Price</th>
                <th className="pb-2">Unrealized P&L</th>
              </tr>
            </thead>
            <tbody>
              {status.positions.map((pos) => (
                <tr key={pos.symbol} className="border-b border-gray-700">
                  <td className="py-3 font-bold">{pos.symbol}</td>
                  <td className="py-3">{pos.quantity}</td>
                  <td className="py-3">${pos.entry_price.toFixed(2)}</td>
                  <td className="py-3">${pos.current_price.toFixed(2)}</td>
                  <td className={`py-3 font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    ${pos.unrealized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-400">No active positions</p>
        )}
      </div>

      {/* Performance Chart */}
      <div className="bg-gray-800 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-bold mb-4">Performance (30 Days)</h2>
        <PerformanceChart data={performance?.daily_pnl ?? []} />
      </div>

      {/* Trade Log */}
      <div className="bg-gray-800 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-bold mb-4">Recent Trades</h2>
        <div className="max-h-96 overflow-y-auto">
          {trades.map((trade) => (
            <div key={trade.id} className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">{new Date(trade.timestamp).toLocaleString()}</span>
              <span className={trade.action === 'BUY' ? 'text-green-500' : 'text-red-500'}>
                {trade.action}
              </span>
              <span className="font-bold">{trade.symbol}</span>
              <span>{trade.quantity} @ ${trade.entry_price.toFixed(2)}</span>
              {trade.pnl !== 0 && (
                <span className={trade.pnl > 0 ? 'text-green-500' : 'text-red-500'}>
                  ${trade.pnl.toFixed(2)}
                </span>
              )}
            </div>
          ))}
          {trades.length === 0 && <p className="text-gray-400">No trades yet</p>}
        </div>
      </div>

      {/* Screener Results */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-bold mb-4">
          Stock Screener (Top 10)
        </h2>
        {screener.slice(0, 10).map((stock, idx) => (
          <div key={stock.symbol} className="flex justify-between py-2 border-b border-gray-700">
            <span className="text-gray-400">#{idx + 1}</span>
            <span className="font-bold">{stock.symbol}</span>
            <span>${stock.price?.toFixed(2)}</span>
            <span className="text-sm text-gray-400">{(stock.avg_volume / 1_000_000).toFixed(1)}M vol</span>
            <span className="text-green-500">Score: {stock.score?.toFixed(2)}</span>
          </div>
        ))}
        {screener.length === 0 && <p className="text-gray-400">No screener data — runs at 9:15 AM ET</p>}
      </div>
    </div>
  );
}

export default Dashboard;
