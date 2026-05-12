import React, { useState } from 'react';
import api from './api';

function KillSwitch({ positions, onKill }) {
  const [armed, setArmed] = useState(false);
  const [loading, setLoading] = useState(false);

  const hasPositions = positions.length > 0;

  const handleClick = async () => {
    if (!armed) { setArmed(true); return; }
    setLoading(true);
    try {
      await api.killSwitch();
      setArmed(false);
      onKill();
    } catch (err) {
      alert('Failed to close positions: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px',
      borderColor: armed ? 'rgba(255,45,85,0.4)' : 'var(--border)',
      transition: 'border-color 0.3s',
      background: armed ? 'rgba(61,0,14,0.4)' : 'var(--panel)',
    }}>
      {/* Left: label + position count */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div className="sect-label" style={{ color: 'rgba(255,45,85,0.6)', letterSpacing: '0.22em' }}>
          EMERGENCY
        </div>
        <div style={{
          width: 1,
          height: 16,
          background: 'var(--border-hi)',
        }} />
        <div style={{ fontSize: 12, color: 'var(--cream-mid)', fontFamily: '"IBM Plex Mono", monospace' }}>
          {hasPositions
            ? <><span style={{ color: 'var(--cream)' }}>{positions.length}</span> open position{positions.length !== 1 ? 's' : ''}</>
            : 'no open positions'}
        </div>
      </div>

      {/* Right: buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {armed && (
          <button
            onClick={() => setArmed(false)}
            disabled={loading}
            className="btn-ghost"
          >
            CANCEL
          </button>
        )}
        <button
          onClick={handleClick}
          disabled={!hasPositions || loading}
          className={armed ? 'btn-kill-armed' : 'btn-kill-idle'}
        >
          {loading
            ? 'CLOSING...'
            : armed
            ? `CONFIRM — CLOSE ${positions.length}`
            : 'CLOSE ALL'}
        </button>
      </div>
    </div>
  );
}

export default KillSwitch;
