import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  ArrowLeft, Send, UserCheck, ArrowRightLeft, CheckCircle,
  Pause, Play, X, Lock, MessageSquare, FileText, Clock,
  Paperclip, Image, Film, Music, File, Download,
} from 'lucide-react';

const STATUS_FLOW = {
  open: [{ value: 'assigned', label: 'Pick Up', icon: UserCheck }],
  assigned: [
    { value: 'in_progress', label: 'Start Working', icon: Play },
    { value: 'on_hold', label: 'Put On Hold', icon: Pause },
  ],
  in_progress: [
    { value: 'on_hold', label: 'Hold', icon: Pause },
    { value: 'resolved', label: 'Resolve', icon: CheckCircle },
  ],
  on_hold: [
    { value: 'in_progress', label: 'Resume', icon: Play },
    { value: 'resolved', label: 'Resolve', icon: CheckCircle },
  ],
  resolved: [
    { value: 'closed', label: 'Close', icon: X },
    { value: 'in_progress', label: 'Reopen', icon: Play },
  ],
};

// ── Media Display Component ──────────────────────────────────────────────────

function MediaContent({ msg }) {
  if (!msg.media_url) return null;

  if (msg.media_type === 'image') {
    return (
      <img
        src={msg.media_url}
        alt={msg.media_filename || 'Image'}
        className="max-w-full max-h-72 rounded-lg mb-2 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={() => window.open(msg.media_url, '_blank')}
        loading="lazy"
      />
    );
  }

  if (msg.media_type === 'video') {
    return (
      <video
        src={msg.media_url}
        controls
        className="max-w-full max-h-72 rounded-lg mb-2"
        preload="metadata"
      />
    );
  }

  if (msg.media_type === 'audio') {
    return (
      <div className="mb-2">
        <audio src={msg.media_url} controls className="w-full" preload="metadata" />
        {msg.media_filename && (
          <p className="text-xs text-gray-400 mt-1">{msg.media_filename}</p>
        )}
      </div>
    );
  }

  // Document / file
  const sizeStr = msg.media_size
    ? msg.media_size > 1048576
      ? `${(msg.media_size / 1048576).toFixed(1)} MB`
      : `${(msg.media_size / 1024).toFixed(0)} KB`
    : '';

  return (
    <a
      href={msg.media_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg mb-2 hover:bg-gray-100 transition-colors group"
    >
      <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
        <File className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{msg.media_filename || 'File'}</p>
        {sizeStr && <p className="text-xs text-gray-400">{sizeStr}</p>}
      </div>
      <Download className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
    </a>
  );
}

// ── File Preview Before Upload ───────────────────────────────────────────────

function FilePreview({ file, onRemove, onSend, sending }) {
  const isImage = file.type.startsWith('image/');
  const isVideo = file.type.startsWith('video/');
  const isAudio = file.type.startsWith('audio/');
  const [preview, setPreview] = useState(null);
  const [caption, setCaption] = useState('');

  useEffect(() => {
    if (isImage) {
      const url = URL.createObjectURL(file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [file, isImage]);

  const sizeStr = file.size > 1048576
    ? `${(file.size / 1048576).toFixed(1)} MB`
    : `${(file.size / 1024).toFixed(0)} KB`;

  return (
    <div className="p-3 border-t border-gray-100 bg-gray-50">
      <div className="flex items-start gap-3">
        {/* Preview */}
        <div className="flex-shrink-0">
          {isImage && preview ? (
            <img src={preview} alt="" className="w-16 h-16 object-cover rounded-lg border" />
          ) : (
            <div className="w-16 h-16 bg-white border rounded-lg flex items-center justify-center">
              {isVideo ? <Film className="w-6 h-6 text-purple-500" /> :
               isAudio ? <Music className="w-6 h-6 text-green-500" /> :
               <File className="w-6 h-6 text-blue-500" />}
            </div>
          )}
        </div>

        {/* File info + caption */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
          <p className="text-xs text-gray-400 mb-2">{sizeStr}</p>
          <input
            type="text"
            value={caption}
            onChange={e => setCaption(e.target.value)}
            placeholder="Add a caption (optional)"
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            onKeyDown={e => {
              if (e.key === 'Enter') onSend(caption);
            }}
          />
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-1.5">
          <button
            onClick={() => onSend(caption)}
            disabled={sending}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
          <button
            onClick={onRemove}
            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-gray-400"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ──────────────────────────────────────────────────────

export default function TicketDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [pendingFile, setPendingFile] = useState(null);
  const [showTransfer, setShowTransfer] = useState(false);
  const [agents, setAgents] = useState([]);
  const [transferTarget, setTransferTarget] = useState('');
  const [transferReason, setTransferReason] = useState('');

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // WebSocket
  const handleWsMessage = useCallback((data) => {
    if (data.type === 'new_message' && data.message) {
      setMessages(prev => {
        if (prev.some(m => m.id === data.message.id)) return prev;
        return [...prev, data.message];
      });
    }
    if (data.type === 'ticket_update' && data.ticket?.id === id) {
      setTicket(prev => prev ? { ...prev, ...data.ticket } : prev);
    }
  }, [id]);

  const { send: wsSend, connected } = useWebSocket(handleWsMessage);

  // Load ticket and messages
  useEffect(() => {
    setLoading(true);
    Promise.all([api.getTicket(id), api.getMessages(id)])
      .then(([t, msgs]) => {
        setTicket(t);
        setMessages(msgs.results || msgs || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    setTimeout(() => { wsSend({ action: 'join_ticket', ticket_id: id }); }, 500);
    return () => { wsSend({ action: 'leave_ticket' }); };
  }, [id]);

  // Poll for new messages every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      api.getMessages(id).then(data => {
        const fresh = data.results || data || [];
        setMessages(prev => fresh.length !== prev.length ? fresh : prev);
      }).catch(() => {});

      api.getTicket(id).then(t => {
        setTicket(prev => {
          if (!prev || prev.status !== t.status || prev.assigned_agent !== t.assigned_agent) return t;
          return prev;
        });
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [id]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Actions ────────────────────────────────────────────────────────────

  const handlePick = async () => {
    try {
      const updated = await api.pickTicket(id);
      setTicket(updated);
    } catch (err) { alert(err.message); }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      const updated = await api.changeTicketStatus(id, newStatus);
      setTicket(updated);
    } catch (err) { alert(err.message); }
  };

  const handleSend = async () => {
    const text = newMsg.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const msg = await api.sendMessage(id, text, isInternal);
      setMessages(prev => prev.some(m => m.id === msg.id) ? prev : [...prev, msg]);
      setNewMsg('');
      inputRef.current?.focus();
    } catch (err) { alert(err.message); }
    finally { setSending(false); }
  };

  const handleSendMedia = async (caption = '') => {
    if (!pendingFile || sending) return;
    setSending(true);
    try {
      const msg = await api.sendMedia(id, pendingFile, caption, isInternal);
      setMessages(prev => prev.some(m => m.id === msg.id) ? prev : [...prev, msg]);
      setPendingFile(null);
    } catch (err) { alert(err.message); }
    finally { setSending(false); }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) setPendingFile(file);
    e.target.value = '';
  };

  // ── Transfer ───────────────────────────────────────────────────────────

  const openTransfer = async () => {
    try {
      const data = await api.getUsers({ role: 'agent' });
      setAgents((data.results || data || []).filter(a => a.id !== user.id && a.is_active));
      setShowTransfer(true);
    } catch (err) { alert(err.message); }
  };

  const handleTransfer = async () => {
    if (!transferTarget) return;
    try {
      const updated = await api.transferTicket(id, transferTarget, transferReason);
      setTicket(updated);
      setShowTransfer(false);
      setTransferTarget('');
      setTransferReason('');
    } catch (err) { alert(err.message); }
  };

  // ── Render ─────────────────────────────────────────────────────────────

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-400">Loading ticket...</div>;
  if (!ticket) return <div className="flex items-center justify-center h-64 text-gray-400">Ticket not found</div>;

  const isMyTicket = ticket.assigned_agent === user.id;
  const canChat = isMyTicket || user.role === 'super_admin';
  const canPickUp = ticket.status === 'open' && !ticket.assigned_agent;

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] lg:h-[calc(100vh-3rem)]">
      {/* Header */}
      <div className="flex items-start justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tickets')} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              {ticket.ticket_number}
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                ticket.status === 'open' ? 'bg-amber-100 text-amber-700' :
                ticket.status === 'assigned' ? 'bg-blue-100 text-blue-700' :
                ticket.status === 'in_progress' ? 'bg-purple-100 text-purple-700' :
                ticket.status === 'resolved' ? 'bg-green-100 text-green-700' :
                'bg-gray-100 text-gray-600'
              }`}>{ticket.status.replace('_', ' ')}</span>
            </h1>
            <p className="text-sm text-gray-500">
              {ticket.service_name} → {ticket.company_name}
              {ticket.assigned_agent_name && ` · Agent: ${ticket.assigned_agent_name}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-400'}`} />

          {canPickUp && (
            <button onClick={handlePick} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
              <UserCheck className="w-4 h-4" /> Pick Up
            </button>
          )}

          {isMyTicket && (
            <button onClick={openTransfer} className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50">
              <ArrowRightLeft className="w-4 h-4" /> Transfer
            </button>
          )}

          {(STATUS_FLOW[ticket.status] || []).map(action => {
            if (action.value === 'assigned') return null;
            if (!canChat) return null;
            return (
              <button key={action.value} onClick={() => handleStatusChange(action.value)}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50">
                <action.icon className="w-4 h-4" /> {action.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main content */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Sidebar */}
        <div className="hidden lg:block w-72 flex-shrink-0 bg-white border border-gray-200 rounded-xl overflow-y-auto">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-sm text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Ticket Details
            </h3>
          </div>
          <div className="p-4 space-y-3">
            {ticket.form_data && Object.entries(ticket.form_data).map(([key, value]) => (
              <div key={key}>
                <p className="text-xs text-gray-400 uppercase tracking-wide">{key.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-900 mt-0.5">{value || '—'}</p>
              </div>
            ))}
            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400 uppercase tracking-wide">Created</p>
              <p className="text-sm text-gray-900 mt-0.5">{new Date(ticket.created_at).toLocaleString()}</p>
            </div>
            {ticket.assigned_at && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Assigned</p>
                <p className="text-sm text-gray-900 mt-0.5">{new Date(ticket.assigned_at).toLocaleString()}</p>
              </div>
            )}
            {user.role === 'super_admin' && ticket.telegram_username && (
              <div className="pt-3 border-t border-gray-100">
                <p className="text-xs text-red-400 uppercase tracking-wide flex items-center gap-1">
                  <Lock className="w-3 h-3" /> User Info (Admin Only)
                </p>
                <p className="text-sm text-gray-900 mt-1">@{ticket.telegram_username}</p>
                <p className="text-sm text-gray-500">{ticket.telegram_first_name}</p>
              </div>
            )}
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 py-10">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p>No messages yet</p>
              </div>
            )}
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`max-w-[75%] px-4 py-2.5 ${
                  msg.sender_type === 'user' ? 'msg-user ml-0' :
                  msg.sender_type === 'system' ? 'msg-system mx-auto text-center max-w-full' :
                  msg.is_internal_note ? 'bg-yellow-50 border border-yellow-200 rounded-xl ml-auto' :
                  'msg-agent ml-auto'
                }`}
              >
                {msg.sender_type !== 'system' && (
                  <p className="text-xs font-medium mb-1 opacity-60">
                    {msg.sender_type === 'user' ? 'Customer' :
                     msg.is_internal_note ? '🔒 Internal Note' :
                     msg.sender_name || 'Agent'}
                  </p>
                )}

                {/* Media content */}
                <MediaContent msg={msg} />

                {/* Text content */}
                {msg.content && (
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                )}

                <p className="text-xs opacity-40 mt-1 text-right">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* File preview (when a file is selected but not yet sent) */}
          {pendingFile && (
            <FilePreview
              file={pendingFile}
              onRemove={() => setPendingFile(null)}
              onSend={handleSendMedia}
              sending={sending}
            />
          )}

          {/* Message input */}
          {canChat && !['closed', 'resolved'].includes(ticket.status) ? (
            <div className="p-3 border-t border-gray-100">
              {isInternal && (
                <div className="mb-2 px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700 flex items-center gap-1">
                  <Lock className="w-3 h-3" /> Internal note — won't be sent to customer
                </div>
              )}
              <div className="flex items-end gap-2">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={newMsg}
                    onChange={e => setNewMsg(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                    }}
                    placeholder={isInternal ? 'Write internal note...' : 'Type a message...'}
                    rows={1}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    style={{ minHeight: '42px', maxHeight: '120px' }}
                    onInput={e => {
                      e.target.style.height = 'auto';
                      e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                    }}
                  />
                </div>

                {/* File upload */}
                <input ref={fileInputRef} type="file" className="hidden"
                  accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip,.rar,.7z"
                  onChange={handleFileSelect}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2.5 rounded-lg border border-gray-300 text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
                  title="Attach file"
                >
                  <Paperclip className="w-4 h-4" />
                </button>

                {/* Internal note toggle */}
                <button
                  onClick={() => setIsInternal(!isInternal)}
                  className={`p-2.5 rounded-lg border transition-colors ${
                    isInternal ? 'bg-yellow-50 border-yellow-300 text-yellow-700' : 'border-gray-300 text-gray-400 hover:text-gray-600'
                  }`}
                  title={isInternal ? 'Switch to customer message' : 'Switch to internal note'}
                >
                  <Lock className="w-4 h-4" />
                </button>

                {/* Send */}
                <button
                  onClick={handleSend}
                  disabled={!newMsg.trim() || sending}
                  className="p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="p-3 border-t border-gray-100 text-center text-sm text-gray-400">
              {['closed', 'resolved'].includes(ticket.status) ? 'This ticket is resolved' : 'Only the assigned agent can send messages'}
            </div>
          )}
        </div>
      </div>

      {/* Transfer Modal */}
      {showTransfer && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setShowTransfer(false)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Transfer Ticket</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Transfer to</label>
                <select value={transferTarget} onChange={e => setTransferTarget(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  <option value="">Select agent...</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.first_name || a.username} {a.is_online ? '(online)' : '(offline)'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
                <textarea value={transferReason} onChange={e => setTransferReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none" rows={2} />
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowTransfer(false)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                <button onClick={handleTransfer} disabled={!transferTarget}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40">Transfer</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
