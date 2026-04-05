import { useEffect, useState } from 'react';
import api from '../utils/api';
import {
  Plus, ChevronDown, ChevronRight, Edit2, Save, X, Trash2,
  GripVertical, ToggleLeft, ToggleRight, Eye, MessageSquare,
  ArrowUp, ArrowDown, Settings, Type, Hash, Calendar, List, Mail, Phone,
} from 'lucide-react';

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'date', label: 'Date', icon: Calendar },
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'phone', label: 'Phone', icon: Phone },
  { value: 'choice', label: 'Multiple Choice', icon: List },
];

// ── Form Schema Editor ───────────────────────────────────────────────────────

function FormSchemaEditor({ schema, onChange }) {
  const [newField, setNewField] = useState({ key: '', label: '', type: 'text', required: true, options: [] });
  const [newOption, setNewOption] = useState('');

  const addField = () => {
    if (!newField.key || !newField.label) return;
    const field = { ...newField };
    if (field.type !== 'choice') delete field.options;
    // Auto-generate key from label if empty
    if (!field.key) field.key = field.label.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    onChange([...schema, field]);
    setNewField({ key: '', label: '', type: 'text', required: true, options: [] });
  };

  const removeField = (idx) => onChange(schema.filter((_, i) => i !== idx));

  const moveField = (idx, dir) => {
    const newSchema = [...schema];
    const target = idx + dir;
    if (target < 0 || target >= newSchema.length) return;
    [newSchema[idx], newSchema[target]] = [newSchema[target], newSchema[idx]];
    onChange(newSchema);
  };

  const updateField = (idx, updates) => {
    const newSchema = [...schema];
    newSchema[idx] = { ...newSchema[idx], ...updates };
    onChange(newSchema);
  };

  const addOption = () => {
    if (!newOption.trim()) return;
    setNewField({ ...newField, options: [...newField.options, newOption.trim()] });
    setNewOption('');
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500">These fields are shown to users in the Telegram bot when they create a ticket.</p>

      {/* Existing fields */}
      {schema.map((field, idx) => {
        const TypeIcon = FIELD_TYPES.find(t => t.value === field.type)?.icon || Type;
        return (
          <div key={idx} className="flex items-center gap-2 px-3 py-2.5 bg-white border border-gray-200 rounded-lg group">
            <div className="flex flex-col">
              <button onClick={() => moveField(idx, -1)} disabled={idx === 0} className="text-gray-300 hover:text-gray-500 disabled:opacity-30">
                <ArrowUp className="w-3 h-3" />
              </button>
              <button onClick={() => moveField(idx, 1)} disabled={idx === schema.length - 1} className="text-gray-300 hover:text-gray-500 disabled:opacity-30">
                <ArrowDown className="w-3 h-3" />
              </button>
            </div>

            <TypeIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{field.label}</p>
              <p className="text-xs text-gray-400">
                key: {field.key} · {field.type}
                {field.required ? ' · required' : ' · optional'}
                {field.options?.length ? ` · ${field.options.join(', ')}` : ''}
              </p>
            </div>

            <button
              onClick={() => updateField(idx, { required: !field.required })}
              className={`text-xs px-2 py-0.5 rounded-full ${field.required ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-500'}`}
            >
              {field.required ? 'required' : 'optional'}
            </button>

            <button onClick={() => removeField(idx)} className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        );
      })}

      {schema.length === 0 && (
        <div className="text-center py-6 text-gray-400 text-sm border border-dashed border-gray-200 rounded-lg">
          No fields yet. Add your first question below.
        </div>
      )}

      {/* Add new field */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-2">
        <p className="text-xs font-medium text-blue-700">Add New Field</p>
        <div className="grid grid-cols-2 gap-2">
          <input value={newField.label} onChange={e => {
            const label = e.target.value;
            const key = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
            setNewField({ ...newField, label, key });
          }} placeholder="Label (e.g. From which city?)" className="px-2.5 py-1.5 border rounded-lg text-sm" />
          <input value={newField.key} onChange={e => setNewField({ ...newField, key: e.target.value })} placeholder="Key (e.g. from_city)" className="px-2.5 py-1.5 border rounded-lg text-sm font-mono text-xs" />
        </div>
        <div className="flex gap-2">
          <select value={newField.type} onChange={e => setNewField({ ...newField, type: e.target.value })} className="px-2.5 py-1.5 border rounded-lg text-sm bg-white flex-1">
            {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="checkbox" checked={newField.required} onChange={e => setNewField({ ...newField, required: e.target.checked })} className="rounded" />
            Required
          </label>
        </div>

        {newField.type === 'choice' && (
          <div>
            <p className="text-xs text-blue-600 mb-1">Options:</p>
            <div className="flex flex-wrap gap-1 mb-1.5">
              {newField.options.map((opt, i) => (
                <span key={i} className="px-2 py-0.5 bg-white border rounded-full text-xs flex items-center gap-1">
                  {opt}
                  <button onClick={() => setNewField({ ...newField, options: newField.options.filter((_, j) => j !== i) })} className="text-gray-400 hover:text-red-500">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-1">
              <input value={newOption} onChange={e => setNewOption(e.target.value)} placeholder="Add option..." className="flex-1 px-2 py-1 border rounded text-xs"
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addOption(); } }} />
              <button onClick={addOption} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">Add</button>
            </div>
          </div>
        )}

        <button onClick={addField} disabled={!newField.key || !newField.label}
          className="w-full py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-40 flex items-center justify-center gap-1">
          <Plus className="w-3.5 h-3.5" /> Add Field
        </button>
      </div>
    </div>
  );
}

// ── Company Editor ───────────────────────────────────────────────────────────

function CompanyEditor({ company, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState({});
  const [activeTab, setActiveTab] = useState('form'); // form, messages

  const startEdit = () => {
    setData({
      name: company.name,
      icon: company.icon,
      is_active: company.is_active,
      form_schema: company.form_schema || [],
      welcome_message: company.welcome_message || '',
      ticket_created_message: company.ticket_created_message || '',
    });
    setEditing(true);
  };

  const save = async () => {
    await onSave(company.id, data);
    setEditing(false);
  };

  if (!editing) {
    return (
      <div className="py-2.5 flex items-center justify-between border-b border-gray-50 last:border-0 group">
        <div className="flex items-center gap-2">
          <span>{company.icon}</span>
          <span className="text-sm font-medium text-gray-700">{company.name}</span>
          <span className="text-xs text-gray-400">({(company.form_schema || []).length} fields)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`px-2 py-0.5 rounded-full text-xs ${company.is_active ? 'bg-green-50 text-green-600' : 'bg-gray-50 text-gray-500'}`}>
            {company.is_active ? 'Active' : 'Off'}
          </span>
          <button onClick={startEdit} className="p-1 hover:bg-gray-100 rounded text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="py-3 border-b border-blue-100 last:border-0 bg-blue-50/30 -mx-5 px-5 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <input value={data.icon} onChange={e => setData({ ...data, icon: e.target.value })} className="w-10 text-center border rounded text-lg px-1 py-0.5" maxLength={4} />
        <input value={data.name} onChange={e => setData({ ...data, name: e.target.value })} className="flex-1 px-2.5 py-1.5 border rounded-lg text-sm font-medium" />
        <label className="flex items-center gap-1 text-xs cursor-pointer">
          <input type="checkbox" checked={data.is_active} onChange={e => setData({ ...data, is_active: e.target.checked })} className="rounded" />
          Active
        </label>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        <button onClick={() => setActiveTab('form')}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${activeTab === 'form' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
          <Type className="w-3 h-3 inline mr-1" /> Form Fields
        </button>
        <button onClick={() => setActiveTab('messages')}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${activeTab === 'messages' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
          <MessageSquare className="w-3 h-3 inline mr-1" /> Bot Messages
        </button>
      </div>

      {activeTab === 'form' && (
        <FormSchemaEditor schema={data.form_schema} onChange={schema => setData({ ...data, form_schema: schema })} />
      )}

      {activeTab === 'messages' && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Welcome Message (when user selects this company)</label>
            <textarea value={data.welcome_message} onChange={e => setData({ ...data, welcome_message: e.target.value })}
              placeholder="Leave empty for default" className="w-full px-3 py-2 border rounded-lg text-sm resize-none" rows={2} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Ticket Created Message</label>
            <textarea value={data.ticket_created_message} onChange={e => setData({ ...data, ticket_created_message: e.target.value })}
              placeholder="Leave empty for default. Use {ticket_number}, {service}, {company} as variables." className="w-full px-3 py-2 border rounded-lg text-sm resize-none" rows={2} />
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button onClick={() => onDelete(company.id)} className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg flex items-center gap-1">
          <Trash2 className="w-3 h-3" /> Delete
        </button>
        <div className="flex gap-2">
          <button onClick={() => setEditing(false)} className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-white">Cancel</button>
          <button onClick={save} className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1">
            <Save className="w-3 h-3" /> Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function ServicesPage() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});
  const [showAddService, setShowAddService] = useState(false);
  const [showAddCompany, setShowAddCompany] = useState(null);
  const [newService, setNewService] = useState({ name: '', icon: '📋' });
  const [newCompany, setNewCompany] = useState({ name: '', icon: '🏢' });
  const [editingService, setEditingService] = useState(null);
  const [editServiceData, setEditServiceData] = useState({});

  const load = () => {
    setLoading(true);
    api.getServices()
      .then(data => setServices(data.results || data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggle = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));

  const addService = async () => {
    if (!newService.name) return;
    try {
      await api.createService(newService);
      setShowAddService(false);
      setNewService({ name: '', icon: '📋' });
      load();
    } catch (err) { alert(err.message); }
  };

  const updateService = async (id) => {
    try {
      await api.updateService(id, editServiceData);
      setEditingService(null);
      load();
    } catch (err) { alert(err.message); }
  };

  const addCompany = async (serviceId) => {
    if (!newCompany.name) return;
    try {
      await api.createCompany({ ...newCompany, service: serviceId, form_schema: [] });
      setShowAddCompany(null);
      setNewCompany({ name: '', icon: '🏢' });
      load();
    } catch (err) { alert(err.message); }
  };

  const updateCompany = async (id, data) => {
    try {
      await api.updateCompany(id, data);
      load();
    } catch (err) { alert(err.message); }
  };

  const deleteCompany = async (id) => {
    if (!confirm('Delete this company? This cannot be undone.')) return;
    try {
      await api.request('DELETE', `/companies/${id}/`);
      load();
    } catch (err) { alert(err.message); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Services & Configuration</h1>
          <p className="text-sm text-gray-500 mt-1">Manage bot services, companies, forms, and messages</p>
        </div>
        <button onClick={() => setShowAddService(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> Add Service
        </button>
      </div>

      {showAddService && (
        <div className="bg-white rounded-xl border border-blue-200 p-4 mb-4 flex items-center gap-3">
          <input value={newService.icon} onChange={e => setNewService({ ...newService, icon: e.target.value })} className="w-12 text-center px-2 py-2 border rounded-lg text-lg" maxLength={4} />
          <input value={newService.name} onChange={e => setNewService({ ...newService, name: e.target.value })} placeholder="Service name" className="flex-1 px-3 py-2 border rounded-lg text-sm"
            onKeyDown={e => { if (e.key === 'Enter') addService(); }} />
          <button onClick={addService} className="px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"><Save className="w-4 h-4" /></button>
          <button onClick={() => setShowAddService(false)} className="px-3 py-2 border text-sm rounded-lg hover:bg-gray-50"><X className="w-4 h-4" /></button>
        </div>
      )}

      <div className="space-y-3">
        {loading ? (
          <div className="p-10 text-center text-gray-400">Loading...</div>
        ) : services.map(svc => (
          <div key={svc.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Service header */}
            <div className="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50" onClick={() => toggle(svc.id)}>
              <div className="flex items-center gap-3">
                {expanded[svc.id] ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}

                {editingService === svc.id ? (
                  <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                    <input value={editServiceData.icon} onChange={e => setEditServiceData({ ...editServiceData, icon: e.target.value })} className="w-10 text-center border rounded text-lg" maxLength={4} />
                    <input value={editServiceData.name} onChange={e => setEditServiceData({ ...editServiceData, name: e.target.value })} className="px-2 py-1 border rounded-lg text-sm font-semibold" />
                    <button onClick={() => updateService(svc.id)} className="p-1 text-green-600 hover:bg-green-50 rounded"><Save className="w-4 h-4" /></button>
                    <button onClick={() => setEditingService(null)} className="p-1 text-gray-400 hover:bg-gray-100 rounded"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <>
                    <span className="text-xl">{svc.icon}</span>
                    <div>
                      <span className="font-semibold text-gray-900">{svc.name}</span>
                      <span className="text-xs text-gray-400 ml-2">{svc.company_count} companies</span>
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs ${svc.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {svc.is_active ? 'Active' : 'Inactive'}
                </span>
                {editingService !== svc.id && (
                  <button onClick={(e) => {
                    e.stopPropagation();
                    setEditServiceData({ name: svc.name, icon: svc.icon, is_active: svc.is_active });
                    setEditingService(svc.id);
                  }} className="p-1 hover:bg-gray-100 rounded text-gray-400">
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Companies */}
            {expanded[svc.id] && (
              <div className="border-t border-gray-100 px-5 py-3">
                {(svc.companies || []).map(comp => (
                  <CompanyEditor key={comp.id} company={comp} onSave={updateCompany} onDelete={deleteCompany} />
                ))}

                {showAddCompany === svc.id ? (
                  <div className="flex items-center gap-2 mt-3 p-3 bg-gray-50 rounded-lg">
                    <input value={newCompany.icon} onChange={e => setNewCompany({ ...newCompany, icon: e.target.value })} className="w-10 text-center border rounded text-lg px-1 py-0.5" maxLength={4} />
                    <input value={newCompany.name} onChange={e => setNewCompany({ ...newCompany, name: e.target.value })} placeholder="Company name" className="flex-1 px-2.5 py-1.5 border rounded-lg text-sm"
                      onKeyDown={e => { if (e.key === 'Enter') addCompany(svc.id); }} />
                    <button onClick={() => addCompany(svc.id)} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">Add</button>
                    <button onClick={() => setShowAddCompany(null)} className="px-3 py-1.5 border text-sm rounded-lg hover:bg-white">Cancel</button>
                  </div>
                ) : (
                  <button onClick={() => setShowAddCompany(svc.id)}
                    className="mt-3 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium px-2 py-1.5 hover:bg-blue-50 rounded-lg">
                    <Plus className="w-3 h-3" /> Add Company
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
