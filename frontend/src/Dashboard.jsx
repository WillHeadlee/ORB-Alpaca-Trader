import React, { useState, useEffect, useCallback } from 'react';
import PerformanceChart from './PerformanceChart';
import KillSwitch from './KillSwitch';
import api from './api';

/* ─── helpers ─────────────────────────────────────────── */

function fmt(val) {
  const n = parseFloat(val) || 0;
  const sign = n >= 0 ? '+' : '-';
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

function pnlClass(val) {
  if (val > 0) return 'glow-green';
  if (val < 0) return 'glow-red';
  return '';
}

function useClock() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'America/New_York',
      }) + ' ET');
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

/* ─── stat card ───────────────────────────────────────── */

function StatCard({ label, value, sub, colorClass }) {
  return (
    <div className="panel" style={{ padding: '16px 18px' }}>
      <div className="sect-label" style={{ marginBottom: 10 }}>{label}</div>
      <div className={`stat-num font-display ${colorClass || ''}`}>{value}</div>
      {sub && (
        <div style={{
          marginTop: 6,
          fontSize: 10,
          color: 'var(--cream-mid)',
          fontFamily: '"IBM Plex Mono", monospace',
          letterSpacing: '0.06em',
        }}>
          {sub}
        </div>
      )}
    </div>
  );
}

/* ─── section header ──────────────────────────────────── */

function SectionHeader({ label, right }) {
  return (
    <div className="panel-header">
      <span className="sect-label">{label}</span>
      <div style={{
        flex: 1,
        height: 1,
        background: 'var(--border-hi)',
        marginLeft: 8,
        marginRight: right ? 8 : 0,
      }} />
      {right && (
        <span style={{
          fontSize: 10,
          color: 'var(--cream-mid)',
          fontFamily: '"IBM Plex Mono", monospace',
          letterSpacing: '0.06em',
          flexShrink: 0,
        }}>
          {right}
        </span>
      )}
    </div>
  );
}

/* ─── loading screen ──────────────────────────────────── */

function LoadingScreen() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--void)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 14,
    }}>
      <div className="font-display glow-amber" style={{ fontSize: 18, letterSpacing: '0.12em' }}>
        ORB//TRADER
      </div>
      <div className="sect-label" style={{ color: 'var(--cream-mid)' }}>
        LOADING MARKET DATA...
      </div>
    </div>
  );
}

/* ─── Dashboard ───────────────────────────────────────── */

function Dashboard({ onLogout }) {
  const [status, setStatus]       = useState(null);
  const [trades, setTrades]       = useState([]);
  const [performance, setPerf]    = useState(null);
  const [screener, setScreener]   = useState([]);
  const [tab, setTab]             = useState('trades');
  const [loading, setLoading]     = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const clock = useClock();

  const loadData = useCallback(async () => {
    try {
      const [s, t, p, sc] = await Promise.all([
        api.getStatus(),
        api.getTrades(50, 0),
        api.getPerformance('30d'),
        api.getScreenerResults(),
      ]);
      setStatus(s);
      setTrades(t.trades);
      setPerf(p);
      setScreener(sc.results);
      setLoading(false);
      setRefreshKey(k => k + 1);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, [loadData]);

  if (loading) return <LoadingScreen />;

  const running  = status?.bot_status === 'running';
  const pnl30    = performance?.total_pnl ?? 0;
  const todayPnl = status?.today_pnl ?? 0;
  const winRate  = (performance?.win_rate ?? 0) * 100;
  const balance  = status?.account_balance ?? 0;
  const mode     = status?.mode ?? 'paper';
  const positions = status?.positions ?? [];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--void)', display: 'flex', flexDirection: 'column' }}>

      {/* ── TOP BAR ── */}
      <header style={{
        background: 'var(--panel)',
        borderBottom: '1px solid var(--border)',
        padding: '0 20px',
        height: 46,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        {/* Left */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <span className="font-display glow-amber" style={{ fontSize: 15, letterSpacing: '0.10em' }}>
            ORB//TRADER
          </span>

          <div style={{ width: 1, height: 16, background: 'var(--border-hi)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div className={running ? 'dot-live' : 'dot-stopped'} />
            <span className="sect-label" style={{
              color: running ? 'var(--green)' : 'var(--red)',
              fontSize: 9,
            }}>
              {running ? 'LIVE' : 'STOPPED'}
            </span>
          </div>

          <span className={`badge ${mode === 'paper' ? 'badge-paper' : 'badge-live'}`}>
            {mode.toUpperCase()}
          </span>
        </div>

        {/* Right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
          <span style={{
            fontFamily: '"IBM Plex Mono", monospace',
            fontSize: 11,
            color: 'var(--cream-mid)',
            letterSpacing: '0.08em',
          }}>
            {clock}
          </span>
          <span style={{
            fontFamily: '"Share Tech Mono", monospace',
            fontSize: 14,
            letterSpacing: '0.04em',
            color: 'var(--cream)',
          }}>
            ${balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </span>
          <button
            onClick={onLogout}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 9,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: 'var(--cream-dim)',
              transition: 'color 0.15s',
              padding: 0,
            }}
            onMouseEnter={e => e.target.style.color = 'var(--cream-mid)'}
            onMouseLeave={e => e.target.style.color = 'var(--cream-dim)'}
          >
            SIGN OUT
          </button>
        </div>
      </header>

      {/* ── BODY ── */}
      <main style={{ flex: 1, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* ── STAT CARDS ── */}
        <div key={`stats-${refreshKey}`} className="data-refresh" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 10,
        }}>
          <StatCard
            label="Today P&L"
            value={fmt(todayPnl)}
            colorClass={pnlClass(todayPnl) || 'glow-cream'}
          />
          <StatCard
            label="30-Day P&L"
            value={fmt(pnl30)}
            sub={`${performance?.total_trades ?? 0} TRADES`}
            colorClass={pnlClass(pnl30) || 'glow-cream'}
          />
          <StatCard
            label="Win Rate"
            value={`${winRate.toFixed(1)}%`}
            sub={`${performance?.winning_trades ?? 0}W · ${performance?.losing_trades ?? 0}L`}
            colorClass={winRate >= 50 ? 'glow-green' : winRate > 0 ? 'glow-red' : ''}
          />
          <StatCard
            label="Equity"
            value={`$${balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
            colorClass="glow-cream"
          />
        </div>

        {/* ── KILL SWITCH ── */}
        <KillSwitch positions={positions} onKill={loadData} />

        {/* ── PERFORMANCE CHART ── */}
        <div className="panel">
          <SectionHeader
            label="Cumulative P&L"
            right={`30D · ${pnl30 >= 0 ? '+' : ''}$${pnl30.toFixed(2)}`}
          />
          <div style={{ padding: '10px 8px 8px' }}>
            <PerformanceChart data={performance?.daily_pnl ?? []} />
          </div>
        </div>

        {/* ── OPEN POSITIONS ── */}
        {positions.length > 0 && (
          <div className="panel">
            <SectionHeader label="Open Positions" right={`${positions.length} ACTIVE`} />
            <table className="term-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Current</th>
                  <th className="right">Unrealized P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.symbol}>
                    <td className="sym">{p.symbol}</td>
                    <td className="dim">{p.quantity}</td>
                    <td className="dim">${p.entry_price.toFixed(2)}</td>
                    <td className="dim">${p.current_price.toFixed(2)}</td>
                    <td className={`right ${pnlClass(p.unrealized_pnl)}`}>
                      {fmt(p.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── TRADE LOG / SCREENER ── */}
        <div className="panel" style={{ flex: 1 }}>
          {/* Tabs */}
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--border)',
            paddingLeft: 4,
          }}>
            <button
              className={`tab-btn ${tab === 'trades' ? 'active' : ''}`}
              onClick={() => setTab('trades')}
            >
              Trade Log
            </button>
            <button
              className={`tab-btn ${tab === 'screener' ? 'active' : ''}`}
              onClick={() => setTab('screener')}
            >
              Screener
            </button>

            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 14 }}>
              {tab === 'trades' && trades.length > 0 && (
                <span className="sect-label" style={{ color: 'var(--cream-mid)' }}>
                  {trades.length} RECORDS
                </span>
              )}
              {tab === 'screener' && screener.length > 0 && (
                <span className="sect-label" style={{ color: 'var(--cream-mid)' }}>
                  TOP {Math.min(screener.length, 20)}
                </span>
              )}
            </div>
          </div>

          {/* Trade Log */}
          {tab === 'trades' && (
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              {trades.length === 0 ? (
                <div style={{
                  padding: '40px 0',
                  textAlign: 'center',
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 11,
                  color: 'var(--cream-dim)',
                  letterSpacing: '0.12em',
                }}>
                  NO TRADES RECORDED
                </div>
              ) : (
                <table className="term-table">
                  <thead>
                    <tr style={{ position: 'sticky', top: 0, background: 'var(--panel)', zIndex: 1 }}>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th className="right">P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.id}>
                        <td className="dim" style={{ fontSize: 11 }}>
                          {new Date(t.timestamp).toLocaleTimeString([], {
                            hour: '2-digit', minute: '2-digit', hour12: false,
                          })}
                        </td>
                        <td className="sym">{t.symbol}</td>
                        <td style={{
                          color: t.action === 'BUY' ? 'var(--green)' : 'var(--red)',
                          letterSpacing: '0.06em',
                        }}>
                          {t.action}
                        </td>
                        <td className="dim">{t.quantity}</td>
                        <td className="dim">${t.entry_price.toFixed(2)}</td>
                        <td className={`right ${pnlClass(t.pnl)}`}>
                          {t.pnl !== 0 ? fmt(t.pnl) : <span style={{ color: 'var(--cream-dim)' }}>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Screener */}
          {tab === 'screener' && (
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              {screener.length === 0 ? (
                <div style={{
                  padding: '40px 0',
                  textAlign: 'center',
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 11,
                  color: 'var(--cream-dim)',
                  letterSpacing: '0.12em',
                }}>
                  NO SCAN DATA — RUNS AT 09:15 ET
                </div>
              ) : (
                <table className="term-table">
                  <thead>
                    <tr style={{ position: 'sticky', top: 0, background: 'var(--panel)', zIndex: 1 }}>
                      <th>#</th>
                      <th>Symbol</th>
                      <th>Price</th>
                      <th>Avg Vol</th>
                      <th>Volatility</th>
                      <th className="right">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {screener.slice(0, 20).map((s, i) => (
                      <tr key={s.symbol}>
                        <td style={{ color: 'var(--cream-dim)', fontSize: 11 }}>{i + 1}</td>
                        <td className="sym">{s.symbol}</td>
                        <td className="dim">${s.price?.toFixed(2)}</td>
                        <td className="dim">{(s.avg_volume / 1e6).toFixed(1)}M</td>
                        <td className="dim">{s.volatility?.toFixed(2)}%</td>
                        <td className="right glow-amber" style={{ fontSize: 13 }}>
                          {s.score?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>

      </main>
    </div>
  );
}

export default Dashboard;
