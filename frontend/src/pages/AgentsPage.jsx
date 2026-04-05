import { useEffect, useState } from 'react';
import api from '../utils/api';
import { Plus, Circle, Shield, Ban, RotateCcw, ChevronDown, ChevronRight, Check, Edit2, X, Save } from 'lucide-react';

// ── Company Tree Selector ────────────────────────────────────────────────────

function CompanyTreeSelector({ services, selected, onChange }) {
  const [expanded, setExpanded] = useState({});

  const toggle = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));

  const getServiceCompanyIds = (svc) => (svc.companies || []).filter(c => c.is_active).map(c => c.id);

  const isServiceFullySelected = (svc) => {
    const ids = getServiceCompanyIds(svc);
    return ids.length > 0 && ids.every(id => selected.includes(id));
  };

  const isServicePartial = (svc) => {
    const ids = getServiceCompanyIds(svc);
    const count = ids.filter(id => selected.includes(id)).length;
    return count > 0 && count < ids.length;
  };

  const toggleService = (svc) => {
    const ids = getServiceCompanyIds(svc);
    if (isServiceFullySelected(svc)) {
      onChange(selected.filter(id => !ids.includes(id)));
    } else {
      onChange([...new Set([...selected, ...ids])]);
    }
  };

  const toggleCompany = (companyId) => {
    if (selected.includes(companyId)) {
      onChange(selected.filter(id => id !== companyId));
    } else {
      onChange([...selected, companyId]);
    }
  };

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden max-h-64 overflow-y-auto">
      {services.map(svc => {
        const isOpen = expanded[svc.id];
        const full = isServiceFullySelected(svc);
        const partial = isServicePartial(svc);
        const companies = (svc.companies || []).filter(c => c.is_active);

        return (
          <div key={svc.id} className="border-b border-gray-100 last:border-0">
            <div className="flex items-center gap-2 px-3 py-2.5 hover:bg-gray-50 cursor-pointer" onClick={() => toggle(svc.id)}>
              <button onClick={(e) => { e.stopPropagation(); toggle(svc.id); }} className="text-gray-400">
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>

              <button
                onClick={(e) => { e.stopPropagation(); toggleService(svc); }}
                className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  full ? 'bg-blue-600 border-blue-600 text-white' :
                  partial ? 'bg-blue-100 border-blue-400 text-blue-600' :
                  'border-gray-300 hover:border-blue-400'
                }`}
              >
                {full && <Check className="w-3 h-3" />}
                {partial && <div className="w-2 h-0.5 bg-blue-600 rounded" />}
              </button>

              <span className="text-sm font-medium text-gray-800 flex-1">{svc.icon} {svc.name}</span>

              <span className={`text-xs font-medium ${full ? 'text-blue-600' : partial ? 'text-blue-400' : 'text-gray-400'}`}>
                {full ? 'All' : partial ? `${companies.filter(c => selected.includes(c.id)).length}/${companies.length}` : 'None'}
              </span>
            </div>

            {isOpen && (
              <div className="pl-10 pb-2 space-y-0.5">
                {companies.map(comp => {
                  const isSelected = selected.includes(comp.id);
                  return (
                    <label key={comp.id} className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleCompany(comp.id)}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{comp.icon} {comp.name}</span>
                    </label>
                  );
                })}
                {companies.length === 0 && (
                  <p className="text-xs text-gray-400 px-3 py-1">No active companies</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Agent Card ───────────────────────────────────────────────────────────────

function AgentCard({ agent, services, onToggleActive, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({});

  const startEdit = () => {
    setEditData({
      allowed_companies: agent.allowed_companies || [],
      max_concurrent_tickets: agent.max_concurrent_tickets,
      role: agent.role,
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    await onUpdate(agent.id, editData);
    setEditing(false);
  };

  // Count selected services/companies for display
  const companyIds = agent.allowed_companies || [];
  const selectedServices = services.filter(s =>
    (s.companies || []).some(c => companyIds.includes(c.id))
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center font-semibold text-gray-600">
            {(agent.first_name?.[0] || agent.username[0]).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-gray-900">
                {agent.first_name ? `${agent.first_name} ${agent.last_name || ''}`.trim() : agent.username}
              </span>
              <Circle className={`w-2.5 h-2.5 ${agent.is_online ? 'fill-green-500 text-green-500' : 'fill-gray-300 text-gray-300'}`} />
              {agent.role === 'super_admin' && <Shield className="w-3.5 h-3.5 text-amber-500" />}
            </div>
            <p className="text-xs text-gray-500">
              @{agent.username} · {agent.active_ticket_count || 0} active · max {agent.max_concurrent_tickets}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!editing && (
            <>
              {selectedServices.length > 0 ? (
                <div className="flex flex-wrap gap-1 max-w-xs">
                  {selectedServices.slice(0, 4).map(s => (
                    <span key={s.id} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">{s.icon} {s.name}</span>
                  ))}
                  {selectedServices.length > 4 && (
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">+{selectedServices.length - 4}</span>
                  )}
                </div>
              ) : (
                <span className="text-xs text-gray-400">No services assigned</span>
              )}

              <button onClick={startEdit} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400" title="Edit">
                <Edit2 className="w-4 h-4" />
              </button>

              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${agent.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {agent.is_active ? 'Active' : 'Disabled'}
              </span>

              <button onClick={() => onToggleActive(agent.id)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400" title={agent.is_active ? 'Disable' : 'Enable'}>
                {agent.is_active ? <Ban className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
              </button>
            </>
          )}
        </div>
      </div>

      {editing && (
        <div className="px-5 py-4 border-t border-gray-100 bg-gray-50 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
              <select value={editData.role} onChange={e => setEditData({ ...editData, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
                <option value="agent">Agent</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Tickets</label>
              <input type="number" value={editData.max_concurrent_tickets}
                onChange={e => setEditData({ ...editData, max_concurrent_tickets: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" min={1} max={100} />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-2">Access Control (Services & Companies)</label>
            <p className="text-xs text-gray-400 mb-2">Select entire services or expand to pick specific companies</p>
            <CompanyTreeSelector
              services={services}
              selected={editData.allowed_companies}
              onChange={(ids) => setEditData({ ...editData, allowed_companies: ids })}
            />
          </div>

          <div className="flex gap-2 justify-end">
            <button onClick={() => setEditing(false)} className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-white flex items-center gap-1">
              <X className="w-3.5 h-3.5" /> Cancel
            </button>
            <button onClick={saveEdit} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1">
              <Save className="w-3.5 h-3.5" /> Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [agents, setAgents] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    username: '', email: '', password: '', first_name: '', last_name: '',
    role: 'agent', allowed_companies: [], max_concurrent_tickets: 5,
  });
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([api.getUsers(), api.getServices()])
      .then(([u, s]) => {
        setAgents(u.results || u || []);
        setServices(s.results || s || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    setError('');
    try {
      await api.createUser(form);
      setShowCreate(false);
      setForm({ username: '', email: '', password: '', first_name: '', last_name: '', role: 'agent', allowed_companies: [], max_concurrent_tickets: 5 });
      load();
    } catch (err) { setError(err.message); }
  };

  const handleUpdate = async (id, data) => {
    try {
      await api.updateUser(id, data);
      load();
    } catch (err) { alert(err.message); }
  };

  const toggleActive = async (id) => {
    try { await api.toggleUserActive(id); load(); } catch (err) { alert(err.message); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> Add Agent
        </button>
      </div>

      {loading ? (
        <div className="p-10 text-center text-gray-400">Loading...</div>
      ) : (
        <div className="space-y-3">
          {agents.map(agent => (
            <AgentCard key={agent.id} agent={agent} services={services} onToggleActive={toggleActive} onUpdate={handleUpdate} />
          ))}
        </div>
      )}

      {/* Create Agent Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Create New Agent</h3>
            {error && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">First Name</label>
                  <input value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Last Name</label>
                  <input value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Username *</label>
                <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Email *</label>
                <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Password *</label>
                <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
                  <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white">
                    <option value="agent">Agent</option>
                    <option value="super_admin">Super Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Max Tickets</label>
                  <input type="number" value={form.max_concurrent_tickets} onChange={e => setForm({ ...form, max_concurrent_tickets: parseInt(e.target.value) || 5 })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" min={1} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-2">Access Control (Services & Companies)</label>
                <CompanyTreeSelector services={services} selected={form.allowed_companies} onChange={(ids) => setForm({ ...form, allowed_companies: ids })} />
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={handleCreate} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Create Agent</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
