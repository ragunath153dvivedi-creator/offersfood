import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import api from '../utils/api';
import { Ticket, Clock, CheckCircle, User, AlertCircle } from 'lucide-react';

const STAT_CARDS = [
  { key: 'open_tickets', label: 'Open', icon: AlertCircle, color: 'text-amber-600 bg-amber-50' },
  { key: 'my_tickets', label: 'My Active', icon: User, color: 'text-blue-600 bg-blue-50' },
  { key: 'assigned_tickets', label: 'In Progress', icon: Clock, color: 'text-purple-600 bg-purple-50' },
  { key: 'resolved_tickets', label: 'Resolved', icon: CheckCircle, color: 'text-green-600 bg-green-50' },
];

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [recentTickets, setRecentTickets] = useState([]);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.getStats().then(setStats).catch(console.error);
    api.getTickets({ status: 'open' }).then(data => {
      setRecentTickets(data.results || data.slice?.(0, 10) || []);
    }).catch(console.error);
  }, []);

  // Poll dashboard every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      api.getStats().then(setStats).catch(() => {});
      api.getTickets({ status: 'open' }).then(data => {
        setRecentTickets(data.results || data.slice?.(0, 10) || []);
      }).catch(() => {});
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.first_name || user?.username}
        </h1>
        <p className="text-gray-500 mt-1">Here's what's happening today</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {STAT_CARDS.map(card => (
          <div key={card.key} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${card.color}`}>
                <card.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats?.[card.key] ?? '—'}</p>
                <p className="text-xs text-gray-500">{card.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Super Admin extras */}
      {user?.role === 'super_admin' && stats && (
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Agents Online</p>
            <p className="text-xl font-bold">{stats.online_agents} / {stats.total_agents}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500 mb-1">Total Tickets</p>
            <p className="text-xl font-bold">{stats.total_tickets}</p>
          </div>
        </div>
      )}

      {/* Open Tickets */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Open Tickets</h2>
          <button
            onClick={() => navigate('/tickets?status=open')}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            View all →
          </button>
        </div>
        <div className="divide-y divide-gray-50">
          {recentTickets.length === 0 ? (
            <p className="p-5 text-gray-400 text-center">No open tickets</p>
          ) : (
            recentTickets.map(ticket => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/tickets/${ticket.id}`)}
                className="px-5 py-3.5 flex items-center justify-between hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div>
                  <p className="font-medium text-sm text-gray-900">{ticket.ticket_number}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {ticket.service_name} · {ticket.company_name}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    ticket.status === 'open' ? 'bg-amber-100 text-amber-700' :
                    ticket.status === 'assigned' ? 'bg-blue-100 text-blue-700' :
                    ticket.status === 'in_progress' ? 'bg-purple-100 text-purple-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {ticket.status.replace('_', ' ')}
                  </span>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
