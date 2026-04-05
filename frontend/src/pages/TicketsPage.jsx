import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import { Search, Filter } from 'lucide-react';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

const STATUS_COLORS = {
  open: 'bg-amber-100 text-amber-700',
  assigned: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-purple-100 text-purple-700',
  on_hold: 'bg-gray-100 text-gray-700',
  resolved: 'bg-green-100 text-green-700',
  closed: 'bg-gray-200 text-gray-600',
};

export default function TicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const statusFilter = searchParams.get('status') || '';
  const assignedFilter = searchParams.get('assigned_to') || '';
  const searchQuery = searchParams.get('search') || '';

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (statusFilter) params.status = statusFilter;
    if (assignedFilter) params.assigned_to = assignedFilter;
    if (searchQuery) params.search = searchQuery;

    api.getTickets(params)
      .then(data => setTickets(data.results || data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter, assignedFilter, searchQuery]);

  // Poll for new tickets every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (assignedFilter) params.assigned_to = assignedFilter;
      if (searchQuery) params.search = searchQuery;

      api.getTickets(params)
        .then(data => setTickets(data.results || data || []))
        .catch(() => {});
    }, 5000);

    return () => clearInterval(interval);
  }, [statusFilter, assignedFilter, searchQuery]);

  const updateFilter = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    setSearchParams(params);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search tickets..."
            value={searchQuery}
            onChange={e => updateFilter('search', e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        <select
          value={statusFilter}
          onChange={e => updateFilter('status', e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
        >
          {STATUS_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <select
          value={assignedFilter}
          onChange={e => updateFilter('assigned_to', e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="">All Agents</option>
          <option value="me">My Tickets</option>
          <option value="unassigned">Unassigned</option>
        </select>
      </div>

      {/* Ticket List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-400">Loading...</div>
        ) : tickets.length === 0 ? (
          <div className="p-10 text-center text-gray-400">No tickets found</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {tickets.map(ticket => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/tickets/${ticket.id}`)}
                className="px-5 py-4 flex items-center justify-between hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm font-semibold text-gray-900">
                      {ticket.ticket_number}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[ticket.status] || ''}`}>
                      {ticket.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">
                    {ticket.service_name} → {ticket.company_name}
                  </p>
                </div>
                <div className="text-right ml-4">
                  {ticket.assigned_agent_name ? (
                    <p className="text-xs text-gray-500">Agent: {ticket.assigned_agent_name}</p>
                  ) : (
                    <p className="text-xs text-amber-600 font-medium">Unassigned</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(ticket.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
