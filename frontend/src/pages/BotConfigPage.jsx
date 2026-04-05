import { useEffect, useState } from 'react';
import api from '../utils/api';
import { Bot, RefreshCw, Power, AlertTriangle, CheckCircle, Clock, XCircle } from 'lucide-react';

const STATUS_CONFIG = {
  active: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Active' },
  standby: { color: 'bg-blue-100 text-blue-700', icon: Clock, label: 'Standby' },
  banned: { color: 'bg-red-100 text-red-700', icon: XCircle, label: 'Banned' },
  error: { color: 'bg-amber-100 text-amber-700', icon: AlertTriangle, label: 'Error' },
};

export default function BotConfigPage() {
  const [bots, setBots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(null);

  const load = () => {
    setLoading(true);
    api.getBots()
      .then(data => setBots(data.results || data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const healthCheck = async (id) => {
    setChecking(id);
    try {
      const updated = await api.healthCheckBot(id);
      setBots(prev => prev.map(b => b.id === id ? updated : b));
    } catch (err) { alert(err.message); }
    finally { setChecking(null); }
  };

  const activate = async (id) => {
    try {
      await api.activateBot(id);
      load();
    } catch (err) { alert(err.message); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bot Configuration</h1>
          <p className="text-sm text-gray-500 mt-1">Manage Telegram bots and failover</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Bot health info */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 text-sm text-blue-800">
        <p className="font-medium mb-1">How failover works:</p>
        <p>The health monitor checks each bot every 2 minutes. If the active bot goes down, the next standby bot is automatically promoted. Bots are tried in priority order (lower number = higher priority).</p>
      </div>

      {/* Bot list */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-10 text-center text-gray-400">Loading...</div>
        ) : bots.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
            <Bot className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">No bots configured</p>
            <p className="text-sm text-gray-400 mt-1">Add bot tokens via Django admin or the database</p>
          </div>
        ) : bots.map(bot => {
          const status = STATUS_CONFIG[bot.status] || STATUS_CONFIG.error;
          const StatusIcon = status.icon;
          return (
            <div key={bot.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${status.color}`}>
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{bot.name}</h3>
                    <p className="text-sm text-gray-500">
                      {bot.bot_username ? `@${bot.bot_username}` : 'Username not fetched yet'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${status.color}`}>
                    <StatusIcon className="w-3 h-3" /> {status.label}
                  </span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-xs text-gray-400">Priority</p>
                  <p className="font-medium">{bot.priority}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Webhook</p>
                  <p className="font-medium">{bot.is_webhook_set ? '✅ Set' : '❌ Not set'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Last Check</p>
                  <p className="font-medium">
                    {bot.last_health_check ? new Date(bot.last_health_check).toLocaleString() : 'Never'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Created</p>
                  <p className="font-medium">{new Date(bot.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {bot.last_error && (
                <div className="mt-3 p-2.5 bg-red-50 border border-red-100 rounded-lg text-xs text-red-700">
                  <span className="font-medium">Last error:</span> {bot.last_error}
                </div>
              )}

              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => healthCheck(bot.id)}
                  disabled={checking === bot.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${checking === bot.id ? 'animate-spin' : ''}`} />
                  Health Check
                </button>
                {bot.status !== 'active' && (
                  <button
                    onClick={() => activate(bot.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
                  >
                    <Power className="w-3.5 h-3.5" /> Activate
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
