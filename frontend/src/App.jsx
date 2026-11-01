import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Send, 
  Upload, 
  FileSpreadsheet, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Play, 
  Square, 
  RefreshCw, 
  Mail, 
  Building, 
  User, 
  Briefcase, 
  Eye, 
  Terminal, 
  History, 
  Sliders, 
  Sparkles,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Smartphone,
  Monitor,
  Search,
  Key,
  X,
  Clock,
  Zap,
  LogOut,
  Settings
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

// Official Google 'G' icon component
function GoogleGIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

export default function App() {
  // Campaign Mode: 'job' | 'sales'
  const [campaignMode, setCampaignMode] = useState('job');
  
  // Server Status & Profile
  const [serverStatus, setServerStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  // Active Dispatch Provider: 'google' | 'smtp' | 'auto'
  const [selectedProvider, setSelectedProvider] = useState('auto');

  // Google OAuth Modal & Form State
  const [showGoogleSetupModal, setShowGoogleSetupModal] = useState(false);
  const [googleClientId, setGoogleClientId] = useState('');
  const [googleClientSecret, setGoogleClientSecret] = useState('');
  const [savingCreds, setSavingCreds] = useState(false);

  // Recipients
  const [recipients, setRecipients] = useState([]);
  const [recipientsFilename, setRecipientsFilename] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const [leadSearchQuery, setLeadSearchQuery] = useState('');
  const [showAllLeadsModal, setShowAllLeadsModal] = useState(false);

  // Attachments
  const [attachments, setAttachments] = useState([]);
  const [selectedAttachment, setSelectedAttachment] = useState('');
  const [uploadingPdf, setUploadingPdf] = useState(false);

  // Template State
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [htmlTemplate, setHtmlTemplate] = useState('');
  const [txtTemplate, setTxtTemplate] = useState('');
  const [previewContent, setPreviewContent] = useState(null);
  const [editorTab, setEditorTab] = useState('html'); // 'html' | 'text'
  const [devicePreviewMode, setDevicePreviewMode] = useState('desktop'); // 'desktop' | 'mobile'

  // Campaign Settings & Execution
  const [batchLimit, setBatchLimit] = useState(30);
  const [minDelay, setMinDelay] = useState(20);
  const [maxDelay, setMaxDelay] = useState(40);
  const [testEmailAddr, setTestEmailAddr] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const [testMessage, setTestMessage] = useState(null);

  // Live Campaign Progress
  const [campaignState, setCampaignState] = useState({
    is_running: false,
    status: 'IDLE',
    total: 0,
    current_idx: 0,
    success_count: 0,
    failed_count: 0,
    current_target: '',
    current_email: '',
    countdown: 0,
    logs: []
  });

  // History & Views
  const [historyList, setHistoryList] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [historyFilter, setHistoryFilter] = useState('ALL');
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' | 'history'

  const terminalContainerRef = useRef(null);
  const textareaRef = useRef(null);

  // Fetch initial status and templates
  useEffect(() => {
    fetchStatus();
    loadTemplates(campaignMode);
    fetchRecipients();
    fetchHistory();

    // Listen for OAuth completion from popup
    const handleAuthMessage = (event) => {
      if (event.data && event.data.type === 'GOOGLE_AUTH_SUCCESS') {
        fetchStatus();
        setShowGoogleSetupModal(false);
      }
    };
    window.addEventListener('message', handleAuthMessage);
    return () => window.removeEventListener('message', handleAuthMessage);
  }, []);

  // Poll campaign status
  useEffect(() => {
    const interval = setInterval(() => {
      fetchCampaignProgress();
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll terminal box internally
  useEffect(() => {
    if (terminalContainerRef.current) {
      terminalContainerRef.current.scrollTop = terminalContainerRef.current.scrollHeight;
    }
  }, [campaignState.logs]);

  // Update preview when templates or recipients change
  useEffect(() => {
    if (recipients.length > 0 && subjectTemplate) {
      generatePreview(recipients[0]);
    }
  }, [subjectTemplate, htmlTemplate, recipients]);

  const fetchStatus = async () => {
    try {
      setLoadingStatus(true);
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setServerStatus(data);
      if (data.attachments && data.attachments.length > 0 && !selectedAttachment) {
        setAttachments(data.attachments);
        setSelectedAttachment(data.attachments[0].name);
      }
      if (data.active_sender_email) {
        setTestEmailAddr(data.active_sender_email);
      } else if (data.smtp_user) {
        setTestEmailAddr(data.smtp_user);
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    } finally {
      setLoadingStatus(false);
    }
  };

  const loadTemplates = async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/templates`);
      const data = await res.json();
      if (data[mode]) {
        setSubjectTemplate(data[mode].subject);
        setHtmlTemplate(data[mode].html);
        setTxtTemplate(data[mode].txt);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const handleModeChange = (mode) => {
    setCampaignMode(mode);
    loadTemplates(mode);
  };

  const fetchRecipients = async () => {
    try {
      const res = await fetch(`${API_BASE}/recipients`);
      const data = await res.json();
      setRecipients(data.recipients || []);
      setRecipientsFilename(data.filename || '');
    } catch (err) {
      console.error('Failed to fetch recipients:', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      const data = await res.json();
      setHistoryList(data.rows || []);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  const fetchCampaignProgress = async () => {
    try {
      const res = await fetch(`${API_BASE}/campaign/status`);
      const data = await res.json();
      setCampaignState(data);
    } catch (err) {
      // Server might be reloading
    }
  };

  // Google OAuth Flow Trigger
  const handleGoogleSignInClick = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/google/url`);
      const data = await res.json();
      if (!data.configured || !data.url) {
        setShowGoogleSetupModal(true);
        return;
      }

      // Open Google OAuth consent in centered popup window
      const width = 540;
      const height = 660;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      window.open(
        data.url,
        'Google OAuth Login',
        `width=${width},height=${height},left=${left},top=${top},status=no,toolbar=no,menubar=no`
      );
    } catch (err) {
      alert('Failed to connect to Google Auth API.');
    }
  };

  const handleDisconnectGoogle = async () => {
    if (!confirm('Disconnect your Google account and switch back to SMTP?')) return;
    try {
      await fetch(`${API_BASE}/auth/google/disconnect`, { method: 'POST' });
      fetchStatus();
    } catch (err) {
      alert('Error disconnecting Google account.');
    }
  };

  const handleSaveGoogleCreds = async (e) => {
    e.preventDefault();
    if (!googleClientId || !googleClientSecret) {
      alert('Please provide both Client ID and Client Secret.');
      return;
    }
    setSavingCreds(true);
    try {
      const res = await fetch(`${API_BASE}/auth/google/save-credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: googleClientId,
          client_secret: googleClientSecret,
          redirect_uri: 'http://127.0.0.1:8000/api/auth/google/callback'
        }),
      });
      if (res.ok) {
        setShowGoogleSetupModal(false);
        fetchStatus();
        setTimeout(() => {
          handleGoogleSignInClick();
        }, 300);
      } else {
        alert('Failed to save credentials.');
      }
    } catch (err) {
      alert('Error saving credentials.');
    } finally {
      setSavingCreds(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploadingFile(true);
    try {
      const res = await fetch(`${API_BASE}/upload-recipients`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setRecipientsFilename(data.filename);
        fetchRecipients();
      } else {
        alert(data.detail || 'Upload failed');
      }
    } catch (err) {
      alert('Error uploading file');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleAttachmentUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploadingPdf(true);
    try {
      const res = await fetch(`${API_BASE}/upload-attachment`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        fetchStatus();
        setSelectedAttachment(data.filename);
      } else {
        alert(data.detail || 'Attachment upload failed');
      }
    } catch (err) {
      alert('Error uploading attachment');
    } finally {
      setUploadingPdf(false);
    }
  };

  const generatePreview = async (sampleRecipient) => {
    try {
      const res = await fetch(`${API_BASE}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient: sampleRecipient || {
            hr_name: 'Sarah Jenkins',
            company_name: 'NextGen Tech',
            job_role: campaignMode === 'job' ? 'Front End Developer' : 'Web Applications'
          },
          subject_template: subjectTemplate,
          html_template: htmlTemplate,
          txt_template: txtTemplate,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewContent(data);
      }
    } catch (err) {
      console.error('Preview error:', err);
    }
  };

  const handleSendTestEmail = async () => {
    if (!testEmailAddr) {
      alert('Please enter a valid test email address.');
      return;
    }
    setSendingTest(true);
    setTestMessage(null);
    try {
      const res = await fetch(`${API_BASE}/test-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_email: testEmailAddr,
          recipient: recipients[0] || null,
          subject_template: subjectTemplate,
          html_template: htmlTemplate,
          txt_template: txtTemplate,
          attachment_name: selectedAttachment,
          provider: selectedProvider,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setTestMessage({ type: 'success', text: data.message || `Test delivered to ${testEmailAddr}!` });
      } else {
        setTestMessage({ type: 'error', text: data.detail || 'Failed to send test email.' });
      }
    } catch (err) {
      setTestMessage({ type: 'error', text: 'Network error connecting to API.' });
    } finally {
      setSendingTest(false);
    }
  };

  const handleStartCampaign = async () => {
    if (recipients.length === 0) {
      alert('No recipients loaded. Please upload an Excel sheet first.');
      return;
    }
    const leadCount = Math.min(Number(batchLimit), recipients.length);
    const provName = isGoogleConnected ? 'Google OAuth (Gmail API)' : 'SMTP';
    if (!confirm(`Launch live dispatch to ${leadCount} leads via ${provName}?`)) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/campaign/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_limit: Number(batchLimit),
          min_delay: Number(minDelay),
          max_delay: Number(maxDelay),
          subject_template: subjectTemplate,
          html_template: htmlTemplate,
          txt_template: txtTemplate,
          attachment_name: selectedAttachment,
          provider: selectedProvider,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || 'Could not start campaign');
      }
    } catch (err) {
      alert('Failed to trigger campaign execution');
    }
  };

  const handleStopCampaign = async () => {
    try {
      await fetch(`${API_BASE}/campaign/stop`, { method: 'POST' });
    } catch (err) {
      alert('Failed to request stop');
    }
  };

  const insertVariable = (varName) => {
    const tag = `{{ ${varName} }}`;
    const textarea = textareaRef.current;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = htmlTemplate;
      const before = text.substring(0, start);
      const after = text.substring(end, text.length);
      const newText = before + tag + after;
      setHtmlTemplate(newText);
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + tag.length;
        textarea.focus();
      }, 0);
    } else {
      setHtmlTemplate((prev) => prev + ` ${tag}`);
    }
  };

  // Filtered Leads
  const filteredRecipients = useMemo(() => {
    if (!leadSearchQuery.trim()) return recipients;
    const q = leadSearchQuery.toLowerCase();
    return recipients.filter((r) => 
      (r.hr_name && r.hr_name.toLowerCase().includes(q)) ||
      (r.hr_email && r.hr_email.toLowerCase().includes(q)) ||
      (r.company_name && r.company_name.toLowerCase().includes(q)) ||
      (r.job_role && r.job_role.toLowerCase().includes(q))
    );
  }, [recipients, leadSearchQuery]);

  // Filtered History
  const filteredHistory = useMemo(() => {
    return historyList.filter((item) => {
      const matchSearch = !historySearch.trim() || 
        (item.hr_email && item.hr_email.toLowerCase().includes(historySearch.toLowerCase())) ||
        (item.company_name && item.company_name.toLowerCase().includes(historySearch.toLowerCase())) ||
        (item.job_role && item.job_role.toLowerCase().includes(historySearch.toLowerCase()));
      const matchFilter = historyFilter === 'ALL' || item.status === historyFilter;
      return matchSearch && matchFilter;
    });
  }, [historyList, historySearch, historyFilter]);

  // Campaign Calculations
  const leadsToDispatch = Math.min(Number(batchLimit) || 1, recipients.length || 1);
  const avgDelaySec = ((Number(minDelay) || 20) + (Number(maxDelay) || 40)) / 2;
  const estMinutes = Math.round((leadsToDispatch * avgDelaySec) / 60);
  const emailsPerHour = Math.round(3600 / avgDelaySec);

  // Template word count
  const wordCount = useMemo(() => {
    const plain = htmlTemplate.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    return plain ? plain.split(' ').length : 0;
  }, [htmlTemplate]);

  const readTimeSec = Math.round((wordCount / 200) * 60);

  const isGoogleConnected = Boolean(serverStatus?.google_auth?.is_connected);
  const googleEmail = serverStatus?.google_auth?.email;
  const googleName = serverStatus?.google_auth?.name;
  const googlePicture = serverStatus?.google_auth?.picture;

  const progressPercent = campaignState.total > 0
    ? Math.round((campaignState.current_idx / campaignState.total) * 100)
    : 0;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 28px', minHeight: '100vh' }}>
      
      {/* Top Navbar & Identity Bar */}
      <header className="glass-card" style={{ padding: '16px 24px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Left: Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'linear-gradient(135deg, #6366f1 0%, #0ea5e9 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)' }}>
            <Mail size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '19px', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Outreach Engine
              </h1>
              <span className="badge badge-primary" style={{ fontSize: '10px' }}>v2.0</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px' }}>
              Targeted Cold Outreach & Candidate Dispatch System
            </p>
          </div>
        </div>

        {/* Center: Auth Connection Card (Google OAuth vs SMTP) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(0, 0, 0, 0.35)', padding: '6px 12px', borderRadius: '14px', border: '1px solid var(--border-color)' }}>
          {isGoogleConnected ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {googlePicture ? (
                <img src={googlePicture} alt="Avatar" style={{ width: '32px', height: '32px', borderRadius: '50%', border: '2px solid #10b981' }} />
              ) : (
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#10b981', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '13px' }}>
                  {googleName ? googleName.charAt(0) : 'G'}
                </div>
              )}
              <div style={{ textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc' }}>{googleName || 'Google User'}</span>
                  <span className="badge badge-emerald" style={{ padding: '1px 6px', fontSize: '10px' }}>
                    <span className="pulse-dot"></span> Gmail API Active
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{googleEmail}</div>
              </div>
              <button 
                onClick={handleDisconnectGoogle}
                title="Disconnect Google Account"
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
              >
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button 
                className="btn btn-google" 
                onClick={handleGoogleSignInClick}
                style={{ padding: '7px 14px', fontSize: '12.5px', borderRadius: '10px' }}
              >
                <GoogleGIcon size={16} /> Sign in with Google
              </button>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>or</span>
              <span className="badge badge-amber" style={{ fontSize: '11px' }}>
                SMTP: {serverStatus?.smtp_user || 'rohanmore151@gmail.com'}
              </span>
              <button
                onClick={() => setShowGoogleSetupModal(true)}
                title="Google API Credentials Settings"
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
              >
                <Settings size={15} />
              </button>
            </div>
          )}
        </div>

        {/* Right: Dual Mode Switcher & View Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(0, 0, 0, 0.4)', padding: '3px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <button
              onClick={() => handleModeChange('job')}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                background: campaignMode === 'job' ? 'var(--primary)' : 'transparent',
                color: campaignMode === 'job' ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease',
              }}
            >
              <Briefcase size={14} /> Job Application
            </button>
            <button
              onClick={() => handleModeChange('sales')}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                background: campaignMode === 'sales' ? 'var(--primary)' : 'transparent',
                color: campaignMode === 'sales' ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease',
              }}
            >
              <Sparkles size={14} /> B2B Outreach
            </button>
          </div>

          {/* Navigation Tabs */}
          <button 
            className="btn btn-secondary"
            onClick={() => setActiveView('dashboard')}
            style={{ 
              borderColor: activeView === 'dashboard' ? 'var(--primary)' : 'var(--border-color)', 
              color: activeView === 'dashboard' ? '#a5b4fc' : 'var(--text-muted)',
              fontSize: '13px'
            }}
          >
            <Sliders size={15} /> Studio
          </button>
          <button 
            className="btn btn-secondary"
            onClick={() => { setActiveView('history'); fetchHistory(); }}
            style={{ 
              borderColor: activeView === 'history' ? 'var(--primary)' : 'var(--border-color)', 
              color: activeView === 'history' ? '#a5b4fc' : 'var(--text-muted)',
              fontSize: '13px'
            }}
          >
            <History size={15} /> Sent Log ({serverStatus?.total_emails_sent || 0})
          </button>
        </div>

      </header>

      {/* VIEW 1: STUDIO DASHBOARD */}
      {activeView === 'dashboard' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 1.15fr)', gap: '24px' }}>
          
          {/* LEFT COLUMN: Leads, PDF, Anti-Spam Safety, & Console */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Step 1: Recruiter / Lead Sheet Card */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <FileSpreadsheet size={18} color="#34d399" />
                  </div>
                  <div>
                    <h2 style={{ fontSize: '15px', fontWeight: 700 }}>1. Recruiter / Target Lead List</h2>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      Active: <span style={{ color: '#38bdf8' }}>{recipientsFilename || 'None loaded'}</span> ({recipients.length} total contacts)
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  {recipients.length > 5 && (
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => setShowAllLeadsModal(true)}
                      style={{ fontSize: '12px', padding: '6px 12px' }}
                    >
                      View All ({recipients.length})
                    </button>
                  )}
                  <label className="btn btn-secondary" style={{ cursor: 'pointer', fontSize: '12px', padding: '6px 12px' }}>
                    <Upload size={14} /> Upload Sheet
                    <input type="file" accept=".xlsx,.xls,.csv" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>

              {/* Table search filter */}
              {recipients.length > 0 && (
                <div style={{ position: 'relative', marginBottom: '10px' }}>
                  <Search size={14} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '10px' }} />
                  <input
                    type="text"
                    className="input-control"
                    placeholder="Search loaded contacts by name, company, email..."
                    value={leadSearchQuery}
                    onChange={(e) => setLeadSearchQuery(e.target.value)}
                    style={{ paddingLeft: '34px', fontSize: '12.5px', padding: '7px 12px 7px 34px' }}
                  />
                </div>
              )}

              {/* Table preview */}
              <div style={{ maxHeight: '185px', overflowY: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.2)' }}>
                {recipients.length === 0 ? (
                  <div style={{ padding: '26px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '13px' }}>
                    No leads loaded. Click "Upload Sheet" to drop an Excel or CSV file.
                  </div>
                ) : (
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Company</th>
                        <th>Role / Service</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRecipients.slice(0, 5).map((r, i) => (
                        <tr key={i}>
                          <td style={{ color: 'var(--text-dim)' }}>{i + 1}</td>
                          <td>{r.hr_name || <span style={{ color: 'var(--text-dim)' }}>Hiring Manager</span>}</td>
                          <td style={{ color: '#38bdf8' }}>{r.hr_email}</td>
                          <td><strong>{r.company_name || 'N/A'}</strong></td>
                          <td style={{ color: '#a5b4fc' }}>{r.job_role || 'Default'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              {filteredRecipients.length > 5 && (
                <p style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '8px', textAlign: 'right' }}>
                  Showing 5 of {filteredRecipients.length} filtered leads
                </p>
              )}
            </div>

            {/* Step 2: Attachment Selection & Upload */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <FileText size={18} color="#a5b4fc" />
                  </div>
                  <div>
                    <h2 style={{ fontSize: '15px', fontWeight: 700 }}>2. Document Attachment (PDF)</h2>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      Attached to outgoing emails: <span style={{ color: '#a5b4fc' }}>{selectedAttachment || 'None selected'}</span>
                    </p>
                  </div>
                </div>

                <label className="btn btn-secondary" style={{ cursor: 'pointer', fontSize: '12px', padding: '6px 12px' }}>
                  <Upload size={14} /> Upload PDF
                  <input type="file" accept=".pdf" onChange={handleAttachmentUpload} style={{ display: 'none' }} />
                </label>
              </div>

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {attachments.length === 0 ? (
                  <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>No PDF attachments found. Click "Upload PDF" above.</div>
                ) : (
                  attachments.map((att, idx) => (
                    <div 
                      key={idx}
                      onClick={() => setSelectedAttachment(att.name)}
                      style={{
                        padding: '8px 14px',
                        borderRadius: '9px',
                        border: `1.5px solid ${selectedAttachment === att.name ? 'var(--primary)' : 'var(--border-color)'}`,
                        background: selectedAttachment === att.name ? 'rgba(99, 102, 241, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <FileText size={15} color={selectedAttachment === att.name ? '#a5b4fc' : 'var(--text-dim)'} />
                      <div>
                        <div style={{ fontSize: '12.5px', fontWeight: 600 }}>{att.name}</div>
                        <div style={{ fontSize: '10.5px', color: 'var(--text-dim)' }}>{att.size_kb} KB</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Step 3: Anti-Spam Safety, Pacing Calculator & Dispatcher */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <h2 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShieldCheck size={18} color="#38bdf8" /> 3. Anti-Spam Safety & Live Dispatcher
                </h2>
                <span className="badge badge-sky" style={{ fontSize: '11px' }}>
                  Channel: {isGoogleConnected ? 'Google OAuth (Gmail API)' : 'SMTP App Password'}
                </span>
              </div>

              {/* Safety Duration Calculator Card */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: 'rgba(0, 0, 0, 0.25)', padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '18px' }}>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> Est. Duration
                  </div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
                    ~{estMinutes} min
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Zap size={12} /> Safe Pacing
                  </div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
                    ~{emailsPerHour} / hr
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <ShieldCheck size={12} /> Daily Safety Cap
                  </div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#fcd34d', marginTop: '2px' }}>
                    {serverStatus?.total_emails_sent || 0} / 500
                  </div>
                </div>
              </div>

              {/* Inputs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ fontSize: '11.5px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Batch Target Limit
                  </label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={batchLimit} 
                    onChange={(e) => setBatchLimit(e.target.value)}
                    min="1" 
                    max="100"
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11.5px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Min Delay (sec)
                  </label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={minDelay} 
                    onChange={(e) => setMinDelay(e.target.value)}
                    min="10" 
                    max="60"
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11.5px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Max Delay (sec)
                  </label>
                  <input 
                    type="number" 
                    className="input-control" 
                    value={maxDelay} 
                    onChange={(e) => setMaxDelay(e.target.value)}
                    min="20" 
                    max="120"
                  />
                </div>
              </div>

              {/* Dispatch Action Button */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                {!campaignState.is_running ? (
                  <button 
                    className="btn btn-primary" 
                    onClick={handleStartCampaign}
                    style={{ flex: 1, padding: '13px 20px', fontSize: '14.5px' }}
                  >
                    <Play size={17} /> Launch Campaign ({Math.min(Number(batchLimit) || 0, recipients.length)} Leads)
                  </button>
                ) : (
                  <button 
                    className="btn btn-danger" 
                    onClick={handleStopCampaign}
                    style={{ flex: 1, padding: '13px 20px', fontSize: '14.5px' }}
                  >
                    <Square size={17} /> Pause / Halt Campaign
                  </button>
                )}
              </div>

              {/* Single Test Email to Me */}
              <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input 
                  type="email" 
                  className="input-control" 
                  placeholder="your_test_email@gmail.com"
                  value={testEmailAddr}
                  onChange={(e) => setTestEmailAddr(e.target.value)}
                  style={{ flex: 1, fontSize: '12.5px' }}
                />
                <button 
                  className="btn btn-secondary" 
                  onClick={handleSendTestEmail}
                  disabled={sendingTest}
                  style={{ whiteSpace: 'nowrap', fontSize: '12.5px' }}
                >
                  {sendingTest ? <RefreshCw size={14} className="spin" /> : <Send size={14} />} Send Test to Me
                </button>
              </div>

              {testMessage && (
                <div style={{ 
                  marginTop: '10px', 
                  fontSize: '12px', 
                  padding: '7px 12px', 
                  borderRadius: '6px',
                  background: testMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                  color: testMessage.type === 'success' ? '#34d399' : '#fca5a5',
                  border: `1px solid ${testMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`
                }}>
                  {testMessage.text}
                </div>
              )}
            </div>

            {/* Live Progress Bar & Execution Console */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={16} color="#34d399" /> Real-Time Execution Console
                </h3>
                {campaignState.countdown > 0 && (
                  <span className="badge badge-amber" style={{ fontSize: '11px' }}>
                    Next send in {campaignState.countdown}s
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div style={{ background: 'rgba(255, 255, 255, 0.08)', borderRadius: '9999px', height: '8px', overflow: 'hidden', marginBottom: '12px' }}>
                <div 
                  style={{ 
                    width: `${progressPercent}%`, 
                    height: '100%', 
                    background: 'linear-gradient(90deg, #6366f1 0%, #10b981 100%)',
                    transition: 'width 0.4s ease'
                  }} 
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', color: 'var(--text-dim)', marginBottom: '12px' }}>
                <span>Dispatched: <strong style={{ color: '#f8fafc' }}>{campaignState.success_count}</strong> / {campaignState.total}</span>
                <span>Failed: <strong style={{ color: campaignState.failed_count > 0 ? '#f43f5e' : 'inherit' }}>{campaignState.failed_count}</strong></span>
                <span>Status: <strong style={{ color: campaignState.is_running ? '#34d399' : '#94a3b8' }}>{campaignState.status}</strong></span>
              </div>

              {/* Terminal Logs Output */}
              <div 
                ref={terminalContainerRef}
                style={{ 
                  height: '150px', 
                  overflowY: 'auto', 
                  background: '#040711', 
                  borderRadius: '8px', 
                  padding: '10px 12px', 
                  fontFamily: 'JetBrains Mono, monospace', 
                  fontSize: '11.5px',
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}
              >
                {campaignState.logs.length === 0 ? (
                  <div style={{ color: '#475569' }}>Logs will stream here upon launching campaign...</div>
                ) : (
                  campaignState.logs.map((log, i) => (
                    <div key={i} style={{ marginBottom: '3px', lineHeight: '1.4' }}>
                      <span style={{ color: '#64748b' }}>[{log.timestamp}]</span>{' '}
                      <span style={{ 
                        color: log.level === 'SUCCESS' ? '#34d399' : log.level === 'ERROR' ? '#f43f5e' : log.level === 'WARNING' ? '#fbbf24' : '#38bdf8',
                        fontWeight: 600
                      }}>
                        [{log.level}]
                      </span>{' '}
                      <span style={{ color: '#e2e8f0' }}>{log.message}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN: Interactive Template Studio & Live Email Simulator */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Dynamic Template Studio */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={17} color="#a5b4fc" />
                  <h2 style={{ fontSize: '15px', fontWeight: 700 }}>Dynamic Email Template Editor</h2>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span className="badge badge-primary">{campaignMode === 'job' ? 'Job Pitch' : 'Sales Outreach'}</span>
                  <span className="badge badge-sky">{wordCount} words · ~{readTimeSec}s read</span>
                </div>
              </div>

              {/* Subject Input */}
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '11.5px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                  Subject Line Template
                </label>
                <input 
                  type="text" 
                  className="input-control" 
                  value={subjectTemplate} 
                  onChange={(e) => setSubjectTemplate(e.target.value)}
                  style={{ fontSize: '13px' }}
                />
              </div>

              {/* Quick Variable Insertion Pills */}
              <div style={{ marginBottom: '12px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginRight: '6px' }}>Quick Insert:</span>
                {['hr_name', 'company_name', 'role', 'sender_name', 'linkedin', 'github', 'phone'].map((v) => (
                  <button
                    key={v}
                    onClick={() => insertVariable(v)}
                    style={{
                      background: 'rgba(99, 102, 241, 0.1)',
                      border: '1px solid rgba(99, 102, 241, 0.25)',
                      color: '#a5b4fc',
                      fontSize: '10.5px',
                      padding: '2.5px 7px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      marginRight: '5px',
                      marginBottom: '5px'
                    }}
                  >
                    + {`{{ ${v} }}`}
                  </button>
                ))}
              </div>

              {/* Body Text Area */}
              <div>
                <label style={{ fontSize: '11.5px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                  Email Body (HTML formatted with Jinja2 placeholders)
                </label>
                <textarea 
                  ref={textareaRef}
                  rows="11"
                  className="input-control" 
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', resize: 'vertical', lineHeight: '1.5' }}
                  value={htmlTemplate} 
                  onChange={(e) => setHtmlTemplate(e.target.value)}
                />
              </div>
            </div>

            {/* Live Recruiter View Simulator (Desktop / Mobile Switcher) */}
            <div className="glass-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Eye size={17} color="#38bdf8" />
                  <h3 style={{ fontSize: '14px', fontWeight: 700 }}>Simulated Recruiter View</h3>
                </div>

                {/* Desktop / Mobile Switcher */}
                <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <button
                    onClick={() => setDevicePreviewMode('desktop')}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      border: 'none',
                      background: devicePreviewMode === 'desktop' ? 'var(--primary)' : 'transparent',
                      color: devicePreviewMode === 'desktop' ? '#fff' : 'var(--text-muted)',
                      fontSize: '11px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Monitor size={12} /> Desktop Gmail
                  </button>
                  <button
                    onClick={() => setDevicePreviewMode('mobile')}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      border: 'none',
                      background: devicePreviewMode === 'mobile' ? 'var(--primary)' : 'transparent',
                      color: devicePreviewMode === 'mobile' ? '#fff' : 'var(--text-muted)',
                      fontSize: '11px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Smartphone size={12} /> Mobile App
                  </button>
                </div>
              </div>

              {/* RENDER SIMULATOR: DESKTOP VS MOBILE */}
              {devicePreviewMode === 'desktop' ? (
                /* Desktop Gmail Card */
                <div style={{ background: '#ffffff', color: '#222222', borderRadius: '10px', padding: '20px', border: '1px solid rgba(255, 255, 255, 0.1)', boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)' }}>
                  <div style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '12px', marginBottom: '14px' }}>
                    <h4 style={{ fontSize: '15.5px', fontWeight: 700, color: '#111827', margin: '0 0 6px 0' }}>
                      {previewContent?.subject || 'Subject Loading...'}
                    </h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12.5px', color: '#4b5563' }}>
                      <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#6366f1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '12px' }}>
                        {previewContent?.sender_user ? previewContent.sender_user.charAt(0).toUpperCase() : 'R'}
                      </div>
                      <div>
                        <strong>{serverStatus?.sender?.name || 'Rohan More'}</strong> <span style={{ color: '#9ca3af', fontSize: '11.5px' }}>&lt;{previewContent?.sender_user || 'sender@gmail.com'}&gt;</span>
                        <div style={{ fontSize: '11px', color: '#9ca3af' }}>to {recipients[0]?.hr_email || 'recruiter@company.com'}</div>
                      </div>
                    </div>
                  </div>

                  <div 
                    style={{ fontSize: '13.5px', lineHeight: '1.6', color: '#1f2937' }}
                    dangerouslySetInnerHTML={{ __html: previewContent?.html || '<p>Rendering email...</p>' }}
                  />

                  {selectedAttachment && (
                    <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #e5e7eb', background: '#f9fafb', display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#374151' }}>
                        <FileText size={15} color="#ef4444" />
                        <strong>{selectedAttachment}</strong>
                        <span style={{ fontSize: '10.5px', color: '#9ca3af' }}>PDF</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Mobile Phone Simulator */
                <div className="mobile-simulator">
                  <div className="mobile-notch"></div>
                  <div style={{ padding: '16px', color: '#1f2937' }}>
                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '8px' }}>Gmail · 9:41 AM</div>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#111827', margin: '0 0 8px 0', lineHeight: '1.3' }}>
                      {previewContent?.subject || 'Subject Loading...'}
                    </h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '10px', borderBottom: '1px solid #e5e7eb' }}>
                      <div style={{ width: '26px', height: '26px', borderRadius: '50%', background: '#6366f1', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '11px' }}>
                        R
                      </div>
                      <div style={{ fontSize: '11px' }}>
                        <strong style={{ display: 'block' }}>{serverStatus?.sender?.name || 'Rohan More'}</strong>
                        <span style={{ color: '#9ca3af' }}>to {recipients[0]?.hr_name || 'Recruiter'}</span>
                      </div>
                    </div>

                    <div 
                      style={{ fontSize: '12px', lineHeight: '1.5', color: '#374151' }}
                      dangerouslySetInnerHTML={{ __html: previewContent?.html || '<p>Rendering email...</p>' }}
                    />

                    {selectedAttachment && (
                      <div style={{ marginTop: '12px', padding: '6px 10px', borderRadius: '6px', background: '#f3f4f6', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px' }}>
                        <FileText size={13} color="#ef4444" />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedAttachment}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>

          </div>

        </div>
      )}

      {/* VIEW 2: SENT AUDIT LOG TABLE */}
      {activeView === 'history' && (
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <History size={20} color="#a5b4fc" />
              <h2 style={{ fontSize: '17px', fontWeight: 700 }}>Sent Delivery Audit Trail</h2>
              <span className="badge badge-primary">{filteredHistory.length} records</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* Search History */}
              <div style={{ position: 'relative' }}>
                <Search size={14} color="var(--text-dim)" style={{ position: 'absolute', left: '10px', top: '9px' }} />
                <input
                  type="text"
                  className="input-control"
                  placeholder="Search logs..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  style={{ paddingLeft: '30px', fontSize: '12px', padding: '6px 12px 6px 30px' }}
                />
              </div>

              {/* Status Filter */}
              <select
                className="input-control"
                value={historyFilter}
                onChange={(e) => setHistoryFilter(e.target.value)}
                style={{ fontSize: '12px', padding: '6px 12px', width: 'auto' }}
              >
                <option value="ALL">All Statuses</option>
                <option value="SUCCESS">Success Only</option>
                <option value="FAILED">Failed Only</option>
              </select>

              <button className="btn btn-secondary" onClick={fetchHistory} style={{ fontSize: '12px', padding: '6px 12px' }}>
                <RefreshCw size={13} /> Refresh
              </button>
            </div>
          </div>

          <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Recipient Email</th>
                  <th>Company</th>
                  <th>Role / Subject</th>
                  <th>Delivery Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ padding: '30px', textAlign: 'center', color: 'var(--text-dim)' }}>
                      No sent history records found matching criteria.
                    </td>
                  </tr>
                ) : (
                  filteredHistory.map((row, i) => (
                    <tr key={i}>
                      <td style={{ color: 'var(--text-dim)' }}>{row.timestamp ? new Date(row.timestamp).toLocaleString() : 'N/A'}</td>
                      <td style={{ color: '#38bdf8', fontWeight: 600 }}>{row.hr_email}</td>
                      <td><strong>{row.company_name || 'N/A'}</strong></td>
                      <td>{row.job_role || 'Default'}</td>
                      <td>
                        <span className={`badge ${row.status === 'SUCCESS' ? 'badge-emerald' : 'badge-danger'}`}>
                          {row.status === 'SUCCESS' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL 1: GOOGLE CLOUD OAUTH SETUP GUIDE */}
      {showGoogleSetupModal && (
        <div className="modal-overlay" onClick={() => setShowGoogleSetupModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <GoogleGIcon size={20} />
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Connect "Sign in with Google"</h3>
              </div>
              <button 
                onClick={() => setShowGoogleSetupModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveGoogleCreds} style={{ padding: '24px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: '1.5' }}>
                To enable 1-click Google Sign-In and send emails via the official Gmail API without an App Password, provide your Google Cloud OAuth credentials:
              </p>

              {/* 3 Step Quick Instructions */}
              <div style={{ background: 'rgba(0, 0, 0, 0.3)', borderRadius: '10px', padding: '14px 16px', marginBottom: '20px', fontSize: '12px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontWeight: 600, color: '#38bdf8', marginBottom: '8px' }}>⚡ 2-Minute Google Cloud Setup:</div>
                <ol style={{ paddingLeft: '18px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
                  <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" style={{ color: '#818cf8', textDecoration: 'underline' }}>Google Cloud Console</a> & enable <strong>Gmail API</strong>.</li>
                  <li>Configure <strong>OAuth Consent Screen</strong> (User Type: External, add your email as Test User).</li>
                  <li>Create <strong>OAuth Client ID</strong> (Web Application):
                    <div style={{ color: '#cbd5e1', fontSize: '11px', marginTop: '2px' }}>
                      Redirect URI: <code style={{ color: '#34d399' }}>http://127.0.0.1:8000/api/auth/google/callback</code>
                    </div>
                  </li>
                </ol>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                  Google Client ID (.apps.googleusercontent.com)
                </label>
                <input
                  type="text"
                  className="input-control"
                  placeholder="e.g. 123456789-abcdef.apps.googleusercontent.com"
                  value={googleClientId}
                  onChange={(e) => setGoogleClientId(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                  Google Client Secret
                </label>
                <input
                  type="password"
                  className="input-control"
                  placeholder="e.g. GOCSPX-xxxxxxxxxxxxxxxx"
                  value={googleClientSecret}
                  onChange={(e) => setGoogleClientSecret(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowGoogleSetupModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={savingCreds}
                >
                  {savingCreds ? <RefreshCw size={14} className="spin" /> : <Key size={14} />} Save & Proceed to Sign-In
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: FULL RECIPIENT INSPECTOR */}
      {showAllLeadsModal && (
        <div className="modal-overlay" onClick={() => setShowAllLeadsModal(false)}>
          <div className="modal-content" style={{ maxWidth: '820px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileSpreadsheet size={18} color="#34d399" />
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>All Loaded Leads ({recipients.length})</h3>
              </div>
              <button 
                onClick={() => setShowAllLeadsModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '16px 24px', maxHeight: '500px', overflowY: 'auto' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Company</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {recipients.map((r, i) => (
                    <tr key={i}>
                      <td style={{ color: 'var(--text-dim)' }}>{i + 1}</td>
                      <td>{r.hr_name || 'Hiring Manager'}</td>
                      <td style={{ color: '#38bdf8' }}>{r.hr_email}</td>
                      <td><strong>{r.company_name || 'N/A'}</strong></td>
                      <td>{r.job_role || 'Default'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
