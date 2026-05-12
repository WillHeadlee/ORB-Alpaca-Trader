import React, { useState } from 'react';
import api from './api';

function KillSwitch({ positions, onKill }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleKillSwitch = async () => {
    if (!showConfirm) {
      setShowConfirm(true);
      return;
    }

    setLoading(true);
    try {
      await api.killSwitch();
      setShowConfirm(false);
      onKill();
      alert('All positions closed successfully');
    } catch (err) {
      alert('Failed to close positions: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg mb-8 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-bold mb-2">Emergency Controls</h2>
        <p className="text-gray-400">Close all open positions immediately</p>
      </div>

      {!showConfirm ? (
        <button
          onClick={handleKillSwitch}
          disabled={positions.length === 0}
          className={`px-8 py-4 text-2xl font-bold rounded-lg shadow-lg transition-all ${
            positions.length > 0
              ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse'
              : 'bg-gray-600 text-gray-400 cursor-not-allowed'
          }`}
        >
          CLOSE ALL POSITIONS
        </button>
      ) : (
        <div className="flex gap-4">
          <button
            onClick={handleKillSwitch}
            disabled={loading}
            className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg"
          >
            {loading ? 'Closing...' : `YES, CLOSE ${positions.length} POSITIONS`}
          </button>
          <button
            onClick={() => setShowConfirm(false)}
            disabled={loading}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white font-bold rounded-lg"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default KillSwitch;
