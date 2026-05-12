import React, { useState } from 'react';
import api from './api';

function KillSwitch({ positions, onKill }) {
  const [armed, setArmed] = useState(false);
  const [killLoading, setKillLoading] = useState(false);

  const [testState, setTestState] = useState('idle'); // idle | confirm | loading | result
  const [testResult, setTestResult] = useState(null);
  const [testError, setTestError] = useState(null);

  const safePositions = positions ?? [];
  const hasPositions = safePositions.length > 0;

  const handleKill = async () => {
    if (!armed) { setArmed(true); return; }
    setKillLoading(true);
    try {
      await api.killSwitch();
      setArmed(false);
      onKill();
    } catch (err) {
      alert('Failed to close positions: ' + err.message);
    } finally {
      setKillLoading(false);
    }
  };

  const handleTestRun = async () => {
    if (testState === 'idle') { setTestState('confirm'); return; }
    if (testState === 'confirm') {
      setTestState('loading');
      setTestResult(null);
      setTestError(null);
      try {
        const result = await api.testRun();
        setTestResult(result);
        setTestState('result');
        onKill(); // refresh dashboard data
      } catch (err) {
        setTestError(err.response?.data?.detail || err.message);
        setTestState('result');
      }
    }
  };

  return (
    <div className="panel" style={{ padding: '10px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>

        {/* LEFT — Test Run */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="sect-label" style={{ color: 'rgba(68,136,204,0.6)', letterSpacing: '0.22em' }}>
            TEST RUN
          </div>
          <div style={{ width: 1, height: 16, background: 'var(--border-hi)' }} />
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {testState === 'confirm' && (
              <button onClick={() => setTestState('idle')} className="btn-ghost" style={{ fontSize: 9 }}>
                CANCEL
              </button>
            )}
            {testState !== 'result' && (
              <button
                onClick={handleTestRun}
                disabled={testState === 'loading'}
                style={{
                  background: testState === 'confirm' ? 'rgba(68,136,204,0.2)' : 'var(--panel-alt)',
                  border: `1px solid ${testState === 'confirm' ? 'var(--blue)' : 'var(--border-hi)'}`,
                  color: testState === 'confirm' ? 'var(--blue)' : 'var(--cream-mid)',
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 9,
                  letterSpacing: '0.15em',
                  textTransform: 'uppercase',
                  padding: '6px 12px',
                  cursor: testState === 'loading' ? 'not-allowed' : 'pointer',
                  opacity: testState === 'loading' ? 0.5 : 1,
                }}
              >
                {testState === 'loading' ? 'RUNNING...' : testState === 'confirm' ? 'CONFIRM — PLACE PAPER ORDER' : 'RUN STRATEGY NOW'}
              </button>
            )}
            {testState === 'result' && testResult && (
              <div style={{ display: 'flex', align: 'center', gap: 10 }}>
                <span style={{ fontSize: 10, fontFamily: '"IBM Plex Mono", monospace', color: 'var(--green)' }}>
                  BUY {testResult.shares} {testResult.symbol} @ ${testResult.entry_price} | stop ${testResult.stop_loss} → ${testResult.take_profit}
                </span>
                <button onClick={() => setTestState('idle')} className="btn-ghost" style={{ fontSize: 9 }}>
                  CLEAR
                </button>
              </div>
            )}
            {testState === 'result' && testError && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 10, fontFamily: '"IBM Plex Mono", monospace', color: 'var(--red)' }}>
                  {testError}
                </span>
                <button onClick={() => setTestState('idle')} className="btn-ghost" style={{ fontSize: 9 }}>
                  CLEAR
                </button>
              </div>
            )}
          </div>
        </div>

        {/* DIVIDER */}
        <div style={{ width: 1, height: 32, background: 'var(--border-hi)', flexShrink: 0 }} />

        {/* RIGHT — Kill Switch */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="sect-label" style={{ color: 'rgba(255,45,85,0.6)', letterSpacing: '0.22em' }}>
            EMERGENCY
          </div>
          <div style={{ width: 1, height: 16, background: 'var(--border-hi)' }} />
          <div style={{ fontSize: 12, color: 'var(--cream-mid)', fontFamily: '"IBM Plex Mono", monospace' }}>
            {hasPositions
              ? <><span style={{ color: 'var(--cream)' }}>{safePositions.length}</span> open position{safePositions.length !== 1 ? 's' : ''}</>
              : 'no open positions'}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {armed && (
              <button onClick={() => setArmed(false)} disabled={killLoading} className="btn-ghost">
                CANCEL
              </button>
            )}
            <button
              onClick={handleKill}
              disabled={!hasPositions || killLoading}
              className={armed ? 'btn-kill-armed' : 'btn-kill-idle'}
            >
              {killLoading ? 'CLOSING...' : armed ? `CONFIRM — CLOSE ${safePositions.length}` : 'CLOSE ALL'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

export default KillSwitch;
