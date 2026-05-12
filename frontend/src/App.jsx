import React, { useState } from 'react';
import Dashboard from './Dashboard';
import api from './api';

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(username, password);
      onLogin();
    } catch {
      setError('AUTH FAILED — INVALID CREDENTIALS');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--void)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Corner decorators */}
      <div style={{
        position: 'absolute', top: 20, left: 20,
        width: 20, height: 20,
        borderTop: '1px solid var(--amber-dim)',
        borderLeft: '1px solid var(--amber-dim)',
      }} />
      <div style={{
        position: 'absolute', bottom: 20, right: 20,
        width: 20, height: 20,
        borderBottom: '1px solid var(--amber-dim)',
        borderRight: '1px solid var(--amber-dim)',
      }} />

      {/* Boot status lines */}
      <div style={{ position: 'absolute', top: 28, left: 40, opacity: 0.5 }}>
        <div className="sect-label" style={{ marginBottom: 3 }}>ALPACA MARKETS // CONNECTED</div>
        <div className="sect-label">SYSTEM READY</div>
      </div>

      <div style={{ position: 'absolute', bottom: 28, right: 40, opacity: 0.5 }}>
        <div className="sect-label" style={{ textAlign: 'right' }}>ORB TRADER v2.0</div>
      </div>

      {/* Login form */}
      <div style={{ width: 300 }}>
        {/* Branding */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div className="sect-label" style={{ marginBottom: 10, color: 'var(--cream-mid)', letterSpacing: '0.28em' }}>
            OPENING RANGE BREAKOUT
          </div>
          <div className="font-display glow-amber" style={{ fontSize: 30, letterSpacing: '0.12em' }}>
            ORB//TRADER
          </div>
          <div className="login-divider" style={{ marginTop: 14 }} />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="sect-label" style={{ marginBottom: 10 }}>AUTHENTICATE</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input
              className="term-input"
              type="text"
              placeholder="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
            <input
              className="term-input"
              type="password"
              placeholder="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div style={{
              marginTop: 10,
              color: 'var(--red)',
              fontSize: 10,
              letterSpacing: '0.10em',
              textTransform: 'uppercase',
              fontFamily: '"IBM Plex Mono", monospace',
            }}>
              ⚠ {error}
            </div>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ marginTop: 14 }}
          >
            {loading ? 'AUTHENTICATING...' : 'SIGN IN →'}
          </button>
        </form>
      </div>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const handleLogout = () => {
    api.clearToken();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <LoginScreen onLogin={() => setIsAuthenticated(true)} />;
  }

  return <Dashboard onLogout={handleLogout} />;
}

export default App;
