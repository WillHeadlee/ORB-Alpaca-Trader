import React, { useState, useEffect } from 'react';
import PerformanceChart from './PerformanceChart';
import KillSwitch from './KillSwitch';
import api from './api';

function StatCard({ label, value, sub, positive }) {
  const color =
    positive === true ? 'text-emerald-400' :
    positive === false ? 'text-red-400' :
    'text-white';
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-widest font-mono mb-1">{label}</p>
      <p className={`text-xl font-mono font-semibold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-zinc-600 mt-1 font-mono">{sub}</p>}
    </div>
  );
}

function StatusDot({ active }) {
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${active ? 'bg-emerald-500' : 'bg-red-500'}`} />
  );
}

function pnlColor(val) {
  if (val > 0) return 'text-emerald-400';
  if (val < 0) return 'text-red-400';
  return 'text-zinc-400';
}

function fmt(val) {
  const n = parseFloat(val) || 0;
  return (n >= 0 ? '+' : '') + '$' + Math.abs(n).toFixed(2);
}

function Dashboard({ onLogout }) {
  const [status, setStatus] = useState(null);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [screener, setScreener] = useState([]);
  const [tab, setTab] = useState('trades');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [s, t, p, sc] = await Promise.all([
        api.getStatus(),
        api.getTrades(50, 0),
        api.getPerformance('30d'),
        api.getScreenerResults(),
      ]);
      setStatus(s);
      setTrades(t.trades);
      setPerformance(p);
      setScreener(sc.results);
      setLoading(false);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <p className="text-zinc-500 text-sm font-mono">Loading...</p>
      </div>
    );
  }

  const running = status?.bot_status === 'running';
  const pnl30 = performance?.total_pnl ?? 0;
  const todayPnl = status?.today_pnl ?? 0;
  const winRate = (performance?.win_rate ?? 0) * 100;

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Top bar */}
      <div className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="text-sm font-mono font-semibold tracking-wide">ORB TRADER</span>
          <div className="flex items-center gap-1 text-xs font-mono text-zinc-400">
            <StatusDot active={running} />
            {running ? 'LIVE' : 'STOPPED'}
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-900">
            {status?.mode?.toUpperCase()}
          </span>
        </div>
        <button
          onClick={onLogout}
          className="text-xs text-zinc-500 hover:text-zinc-300 font-mono transition-colors"
        >
          Sign out
        </button>
      </div>

      <div className="px-6 py-4 space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-4 gap-3">
          <StatCard
            label="Today P&L"
            value={fmt(todayPnl)}
            positive={todayPnl > 0 ? true : todayPnl < 0 ? false : undefined}
          />
          <StatCard
            label="30-Day P&L"
            value={fmt(pnl30)}
            sub={`${performance?.total_trades ?? 0} trades`}
            positive={pnl30 > 0 ? true : pnl30 < 0 ? false : undefined}
          />
          <StatCard
            label="Win Rate"
            value={`${winRate.toFixed(1)}%`}
            sub={`${performance?.winning_trades ?? 0}W / ${performance?.losing_trades ?? 0}L`}
            positive={winRate >= 50 ? true : winRate > 0 ? false : undefined}
          />
          <StatCard
            label="Balance"
            value={`$${(status?.account_balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          />
        </div>

        {/* Kill switch */}
        <KillSwitch positions={status?.positions ?? []} onKill={loadData} />

        {/* Positions */}
        {(status?.positions?.length ?? 0) > 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded">
            <div className="px-4 py-2 border-b border-zinc-800">
              <span className="text-xs text-zinc-500 uppercase tracking-widest font-mono">Open Positions</span>
            </div>
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-left text-xs text-zinc-600 border-b border-zinc-800">
                  <th className="px-4 py-2">Symbol</th>
                  <th className="px-4 py-2">Qty</th>
                  <th className="px-4 py-2">Entry</th>
                  <th className="px-4 py-2">Current</th>
                  <th className="px-4 py-2 text-right">Unreal. P&L</th>
                </tr>
              </thead>
              <tbody>
                {status.positions.map((p) => (
                  <tr key={p.symbol} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-2.5 font-semibold">{p.symbol}</td>
                    <td className="px-4 py-2.5 text-zinc-400">{p.quantity}</td>
                    <td className="px-4 py-2.5 text-zinc-400">${p.entry_price.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-zinc-400">${p.current_price.toFixed(2)}</td>
                    <td className={`px-4 py-2.5 text-right ${pnlColor(p.unrealized_pnl)}`}>
                      {fmt(p.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Chart */}
        <div className="bg-zinc-900 border border-zinc-800 rounded">
          <div className="px-4 py-2 border-b border-zinc-800">
            <span className="text-xs text-zinc-500 uppercase tracking-widest font-mono">Cumulative P&L — 30 Days</span>
          </div>
          <div className="p-4">
            <PerformanceChart data={performance?.daily_pnl ?? []} />
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-zinc-900 border border-zinc-800 rounded">
          <div className="flex border-b border-zinc-800">
            {['trades', 'screener'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2.5 text-xs font-mono uppercase tracking-widest transition-colors ${
                  tab === t
                    ? 'text-white border-b border-white -mb-px'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {t === 'trades' ? 'Trade Log' : 'Screener'}
              </button>
            ))}
          </div>

          {tab === 'trades' && (
            <div className="max-h-80 overflow-y-auto">
              {trades.length === 0 ? (
                <p className="px-4 py-8 text-center text-zinc-600 text-sm font-mono">No trades yet</p>
              ) : (
                <table className="w-full text-sm font-mono">
                  <thead className="sticky top-0 bg-zinc-900">
                    <tr className="text-left text-xs text-zinc-600 border-b border-zinc-800">
                      <th className="px-4 py-2">Time</th>
                      <th className="px-4 py-2">Symbol</th>
                      <th className="px-4 py-2">Side</th>
                      <th className="px-4 py-2">Qty</th>
                      <th className="px-4 py-2">Price</th>
                      <th className="px-4 py-2 text-right">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="px-4 py-2 text-zinc-500">
                          {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="px-4 py-2 font-semibold">{t.symbol}</td>
                        <td className={`px-4 py-2 ${t.action === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
                          {t.action}
                        </td>
                        <td className="px-4 py-2 text-zinc-400">{t.quantity}</td>
                        <td className="px-4 py-2 text-zinc-400">${t.entry_price.toFixed(2)}</td>
                        <td className={`px-4 py-2 text-right ${pnlColor(t.pnl)}`}>
                          {t.pnl !== 0 ? fmt(t.pnl) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {tab === 'screener' && (
            <div className="max-h-80 overflow-y-auto">
              {screener.length === 0 ? (
                <p className="px-4 py-8 text-center text-zinc-600 text-sm font-mono">No scan data — runs at 9:15 AM ET</p>
              ) : (
                <table className="w-full text-sm font-mono">
                  <thead className="sticky top-0 bg-zinc-900">
                    <tr className="text-left text-xs text-zinc-600 border-b border-zinc-800">
                      <th className="px-4 py-2">#</th>
                      <th className="px-4 py-2">Symbol</th>
                      <th className="px-4 py-2">Price</th>
                      <th className="px-4 py-2">Avg Vol</th>
                      <th className="px-4 py-2">Volatility</th>
                      <th className="px-4 py-2 text-right">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {screener.slice(0, 20).map((s, i) => (
                      <tr key={s.symbol} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="px-4 py-2 text-zinc-600">{i + 1}</td>
                        <td className="px-4 py-2 font-semibold">{s.symbol}</td>
                        <td className="px-4 py-2 text-zinc-400">${s.price?.toFixed(2)}</td>
                        <td className="px-4 py-2 text-zinc-400">{(s.avg_volume / 1e6).toFixed(1)}M</td>
                        <td className="px-4 py-2 text-zinc-400">{s.volatility?.toFixed(2)}%</td>
                        <td className="px-4 py-2 text-right text-emerald-400">{s.score?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
