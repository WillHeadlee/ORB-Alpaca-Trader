import React, { useState } from 'react';
import Dashboard from './Dashboard';
import api from './api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(username, password);
      setIsAuthenticated(true);
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.clearToken();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="w-80">
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <span className="text-xs text-zinc-500 uppercase tracking-widest font-mono">ORB TRADER</span>
            </div>
            <h1 className="text-2xl font-semibold text-white">Sign in</h1>
          </div>
          <form onSubmit={handleLogin} className="space-y-3">
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 bg-zinc-900 border border-zinc-800 text-white text-sm rounded focus:outline-none focus:border-zinc-600 placeholder-zinc-600"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 bg-zinc-900 border border-zinc-800 text-white text-sm rounded focus:outline-none focus:border-zinc-600 placeholder-zinc-600"
            />
            {error && <p className="text-red-500 text-xs">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-white text-black text-sm font-medium rounded hover:bg-zinc-200 transition-colors disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return <Dashboard onLogout={handleLogout} />;
}

export default App;
