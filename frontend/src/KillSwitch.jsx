import React, { useState } from 'react';
import api from './api';

function KillSwitch({ positions, onKill }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleKill = async () => {
    if (!showConfirm) { setShowConfirm(true); return; }
    setLoading(true);
    try {
      await api.killSwitch();
      setShowConfirm(false);
      onKill();
    } catch (err) {
      alert('Failed to close positions: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const hasPositions = positions.length > 0;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border border-zinc-800 rounded mb-4">
      <div>
        <span className="text-xs text-zinc-500 uppercase tracking-widest font-mono">Emergency</span>
        <p className="text-sm text-white mt-0.5">
          {hasPositions ? `${positions.length} open position${positions.length > 1 ? 's' : ''}` : 'No open positions'}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {showConfirm && (
          <button
            onClick={() => setShowConfirm(false)}
            disabled={loading}
            className="px-3 py-1.5 text-xs text-zinc-400 border border-zinc-700 rounded hover:border-zinc-500 transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleKill}
          disabled={!hasPositions || loading}
          className={`px-4 py-1.5 text-xs font-mono font-semibold rounded transition-colors ${
            !hasPositions
              ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
              : showConfirm
              ? 'bg-red-600 text-white hover:bg-red-500'
              : 'bg-red-950 text-red-400 border border-red-800 hover:bg-red-900'
          }`}
        >
          {loading ? 'CLOSING...' : showConfirm ? `CONFIRM — CLOSE ${positions.length}` : 'CLOSE ALL'}
        </button>
      </div>
    </div>
  );
}

export default KillSwitch;
