import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Shield,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Terminal,
  Activity,
  GitBranch,
  Code2,
  FileText,
  Lock,
  Check,
  Download,
  Search,
  FlaskConical,
  ShieldCheck,
  GitCommit,
  Bug,
  Copy,
  Layers,
  ExternalLink,
  ChevronRight,
  Flame,
  Clock,
  Server,
  Key,
  Settings,
  X
} from 'lucide-react';
import './index.css';

const API_BASE = 'http://localhost:8000';

const PIPELINE_STEPS = [
  { id: 'observe', label: 'Observe' },
  { id: 'correlate', label: 'Correlate' },
  { id: 'hypothesize', label: 'Hypothesize' },
  { id: 'reproduce', label: 'Reproduce' },
  { id: 'root_cause', label: 'Root Cause' },
  { id: 'patch', label: 'Patch' },
  { id: 'verify', label: 'Verify' },
];

export default function App() {
  const [selectedIncident, setSelectedIncident] = useState('INC-4821');
  const [scenarios, setScenarios] = useState([]);
  const [activeTab, setActiveTab] = useState('runbook');
  const [isRunning, setIsRunning] = useState(false);
  const [stepDelay, setStepDelay] = useState(0.2);
  const [eventsLog, setEventsLog] = useState([]);
  const [copiedPostmortem, setCopiedPostmortem] = useState(false);
  
  const [agentState, setAgentState] = useState({
    status: 'READY',
    confidence: 'PENDING',
    step: 0,
    test_counts: { passed: 0, failed: 0, total: 0 },
    diff_stats: { lines_added: 0, lines_removed: 0 },
    finish_data: null,
    report_markdown: ''
  });

  const [telemetry, setTelemetry] = useState(null);
  const [diffData, setDiffData] = useState({ diff_text: '', lines_added: 0, lines_removed: 0 });
  const [artifacts, setArtifacts] = useState({});
  const [humanApproved, setHumanApproved] = useState(false);
  const [searchQuery, setSearchQuery] = useState('CouponExpired');
  const [searchResults, setSearchResults] = useState([]);
  const [backendConnected, setBackendConnected] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [modelInput, setModelInput] = useState('gpt-4o');
  const [baseUrlInput, setBaseUrlInput] = useState('');
  const [hasApiKey, setHasApiKey] = useState(false);
  const [configStatus, setConfigStatus] = useState('');

  const handleSaveConfig = async (e) => {
    if (e) e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKeyInput,
          model: modelInput,
          base_url: baseUrlInput
        })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        setHasApiKey(data.has_key);
        setConfigStatus('API Key configured! Active mode: ' + data.llm_mode);
        setTimeout(() => {
          setConfigStatus('');
          setShowSettings(false);
        }, 1400);
      }
    } catch {
      setConfigStatus('Error saving API key.');
    }
  };

  const runbookEndRef = useRef(null);

  // Fetch initial scenarios
  const fetchScenarios = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scenarios`);
      const data = await res.json();
      setScenarios(data.scenarios || []);
    } catch {
      // offline fallback
    }
  }, []);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status?incident_id=${selectedIncident}`);
      const data = await res.json();
      setHumanApproved(data.human_approved || false);
      if (data.last_state) setAgentState(data.last_state);
      setBackendConnected(true);
    } catch {
      setBackendConnected(false);
    }
  }, [selectedIncident]);

  // Fetch telemetry
  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/telemetry?incident_id=${selectedIncident}&query=${searchQuery}`);
      const data = await res.json();
      setTelemetry(data);
      setSearchResults(data.log_search || []);
    } catch {
      // offline fallback
    }
  }, [selectedIncident, searchQuery]);

  // Fetch git diff
  const fetchDiff = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/diff`);
      const data = await res.json();
      setDiffData(data);
    } catch {
      // offline fallback
    }
  }, []);

  // Fetch artifacts
  const fetchArtifacts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/artifacts?incident_id=${selectedIncident}`);
      const data = await res.json();
      setArtifacts(data.artifacts || {});
    } catch {
      // offline fallback
    }
  }, [selectedIncident]);

  useEffect(() => {
    fetchScenarios();
    fetchStatus();
    fetchTelemetry();
    fetchDiff();
    fetchArtifacts();
  }, [selectedIncident]);

  useEffect(() => {
    if (runbookEndRef.current) {
      runbookEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [eventsLog]);

  // Reset sandbox environment
  const handleReset = async () => {
    try {
      await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
      setEventsLog([]);
      setHumanApproved(false);
      setTestResult(null);
      setAgentState({
        status: 'READY',
        confidence: 'PENDING',
        step: 0,
        test_counts: { passed: 0, failed: 0, total: 0 },
        diff_stats: { lines_added: 0, lines_removed: 0 },
        finish_data: null,
        report_markdown: ''
      });
      fetchDiff();
      fetchArtifacts();
    } catch {
      // ignore
    }
  };

  // Run automated pytest suite
  const handleRunTests = async () => {
    setIsRunningTests(true);
    try {
      const res = await fetch(`${API_BASE}/api/run-tests`, { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
    } catch {
      // ignore
    } finally {
      setIsRunningTests(false);
    }
  };

  // Human approval
  const handleApprove = async () => {
    try {
      await fetch(`${API_BASE}/api/approve`, { method: 'POST' });
      setHumanApproved(true);
    } catch {
      // ignore
    }
  };

  // Run autonomous investigation stream
  const runInvestigation = async () => {
    setIsRunning(true);
    setEventsLog([]);
    setHumanApproved(false);
    setActiveTab('runbook');

    try {
      const es = new EventSource(`${API_BASE}/api/investigate/stream?incident_id=${selectedIncident}&delay=${stepDelay}`);

      es.onmessage = (event) => {
        if (event.data === '[DONE]') {
          es.close();
          setIsRunning(false);
          fetchDiff();
          fetchArtifacts();
          return;
        }
        try {
          const parsed = JSON.parse(event.data);
          const { tool, summary, current_state: state } = parsed;
          if (state) setAgentState(state);
          const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setEventsLog(prev => [...prev, {
            time: timeStr,
            step: state?.step || prev.length + 1,
            tool: tool || 'execute_step',
            summary: summary || 'Telemetry inspection and AST analysis in progress.'
          }]);
        } catch {
          // ignore parsing errors
        }
      };

      es.onerror = () => {
        es.close();
        setIsRunning(false);
      };
    } catch {
      setIsRunning(false);
    }
  };

  // Copy postmortem markdown
  const copyPostmortem = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedPostmortem(true);
    setTimeout(() => setCopiedPostmortem(false), 2000);
  };

  const currentScenario = scenarios.find(s => s.incident_id === selectedIncident) || {
    incident_id: 'INC-4821',
    title: 'Checkout API elevated 500 errors',
    service: 'checkout',
    severity: 'HIGH',
    deployment: 'v2.4.1',
    description: 'Checkout API error rate increased from 0.8% to 31.4% after deployment v2.4.1.',
    error_rate_before: '0.8%',
    error_rate_after: '31.4%',
    affected_endpoint: '/v1/checkout',
    primary_file: 'app/checkout.py',
    buggy_line_num: 28
  };

  const isVerified = agentState.status === 'VERIFIED';
  const agentStep = agentState.step || 0;

  // Pipeline step status mapper
  const getStepStatus = (index) => {
    if (isVerified) return 'completed';
    if (index + 1 < agentStep) return 'completed';
    if (index + 1 === agentStep) return 'active';
    return 'pending';
  };

  const errorSeries = telemetry?.series?.error_rates_pct || [0.8, 0.7, 0.8, 0.9, 1.2, 14.5, 28.1, 31.4, 30.9, 31.4];
  const maxErr = Math.max(...errorSeries, 1);

  const diffLines = (diffData.diff_text || '').split('\n').filter(Boolean);

  return (
    <div className="app-container">
      {/* ─── OPERATIONAL HEADER ─── */}
      <header className="header">
        <div className="header-left">
          <div className="brand-badge">
            <div className="brand-icon">
              <Shield size={14} />
            </div>
            <span>INCIDENTPILOT</span>
            <span className="version-pill">SRE RUNTIME 2.4</span>
          </div>

          <div className="header-divider" />

          <select
            className="scenario-dropdown"
            value={selectedIncident}
            onChange={e => setSelectedIncident(e.target.value)}
          >
            {scenarios.map(s => (
              <option key={s.incident_id} value={s.incident_id}>
                {s.incident_id} — {s.title} ({s.severity})
              </option>
            ))}
          </select>
        </div>

        <div className="header-right">
          <div className="status-indicator">
            <span className={`status-dot ${backendConnected ? 'active' : 'idle'}`} />
            <span>SANDBOX US-EAST-1</span>
          </div>

          <button
            className="btn btn-secondary"
            onClick={() => setShowSettings(true)}
            title="Configure LLM API Key and Models"
          >
            <Key size={13} color={hasApiKey ? 'var(--color-emerald)' : 'var(--text-muted)'} />
            <span>{hasApiKey ? 'LLM: Active' : 'API Key'}</span>
          </button>

          <button
            className="btn btn-secondary"
            onClick={handleReset}
            disabled={isRunning}
            title="Reset sandbox code and environment to baseline"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          <button
            className="btn btn-primary"
            onClick={runInvestigation}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <Flame size={13} className="animate-spin" />
                <span>Investigating…</span>
              </>
            ) : (
              <>
                <Play size={13} />
                <span>Launch Autonomous Agent</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* ─── API KEY & MODEL CONFIGURATION MODAL ─── */}
      {showSettings && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(5, 7, 12, 0.75)',
          backdropFilter: 'blur(4px)',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-md)',
            width: '460px',
            maxWidth: '92vw',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '13px' }}>
                <Key size={14} color="var(--color-primary)" />
                <span>LLM Credentials & Model Settings</span>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={15} />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 500 }}>
                  LLM API Key (OpenAI / OpenRouter / DeepSeek / Groq)
                </label>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={apiKeyInput}
                  onChange={e => setApiKeyInput(e.target.value)}
                  className="scenario-dropdown"
                  style={{ width: '100%', height: '32px' }}
                />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                  Alternatively, set <code>LLM_API_KEY=...</code> inside <code>incidentpilot/.env</code>
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 500 }}>
                  Model
                </label>
                <input
                  type="text"
                  placeholder="gpt-4o"
                  value={modelInput}
                  onChange={e => setModelInput(e.target.value)}
                  className="scenario-dropdown"
                  style={{ width: '100%', height: '32px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 500 }}>
                  Base URL (Optional — for OpenRouter, Ollama, etc.)
                </label>
                <input
                  type="text"
                  placeholder="https://api.openai.com/v1"
                  value={baseUrlInput}
                  onChange={e => setBaseUrlInput(e.target.value)}
                  className="scenario-dropdown"
                  style={{ width: '100%', height: '32px' }}
                />
              </div>

              {configStatus && (
                <div style={{
                  padding: '8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  background: 'var(--color-primary-subtle)',
                  color: 'var(--color-primary)',
                  border: '1px solid var(--color-primary-border)'
                }}>
                  {configStatus}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowSettings(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Credentials
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── INCIDENT CONTEXT RIBBON (Linear-Style High Density) ─── */}
      <div className="incident-strip">
        <div className="strip-main">
          <span className="badge badge-sev1">SEV-1 CRITICAL</span>
          <span className="badge badge-service">SERVICE: {currentScenario.service.toUpperCase()}</span>
          <span className="strip-title">{currentScenario.title}</span>
        </div>

        <div className="strip-meta">
          <div className="meta-item">
            <span className="meta-label">Endpoint:</span>
            <code className="mono">{currentScenario.affected_endpoint || '/v1/checkout'}</code>
          </div>
          <div className="meta-item">
            <span className="meta-label">Deploy Trigger:</span>
            <code className="mono">{currentScenario.deployment} (commit 8f3b2a1)</code>
          </div>
          <div className="meta-item">
            <span className="meta-label">Error Rate:</span>
            <span className="meta-val-highlight">{currentScenario.error_rate_before} → {currentScenario.error_rate_after}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Status:</span>
            <span style={{ color: isVerified ? 'var(--color-emerald)' : isRunning ? 'var(--color-amber)' : 'var(--text-secondary)', fontWeight: 600 }}>
              {isVerified ? 'VERIFIED FIX READY' : isRunning ? 'INVESTIGATING' : 'INCIDENT ACTIVE'}
            </span>
          </div>
        </div>

        <div className="strip-actions">
          <button
            className="btn btn-secondary"
            onClick={handleRunTests}
            disabled={isRunningTests || isRunning}
            title="Execute pytest test suite"
          >
            <FlaskConical size={13} />
            <span>{isRunningTests ? 'Running tests…' : testResult ? `Tests: ${testResult.passed}/${testResult.total} Passed` : 'Run PyTest'}</span>
          </button>
        </div>
      </div>

      {/* ─── PIPELINE STEPPER ─── */}
      <div className="pipeline-bar">
        {PIPELINE_STEPS.map((step, idx) => {
          const status = getStepStatus(idx);
          return (
            <React.Fragment key={step.id}>
              <div className={`step-node ${status}`}>
                {status === 'completed' && <CheckCircle2 size={12} />}
                {status === 'active' && <Clock size={12} className="animate-spin" />}
                <span>{idx + 1}. {step.label}</span>
              </div>
              {idx < PIPELINE_STEPS.length - 1 && <span className="step-divider">›</span>}
            </React.Fragment>
          );
        })}

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Delay:</span>
          <input
            type="range"
            min="0.05"
            max="0.8"
            step="0.05"
            value={stepDelay}
            onChange={e => setStepDelay(parseFloat(e.target.value))}
            style={{ width: '60px', accentColor: 'var(--color-primary)' }}
          />
          <span className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)', minWidth: '28px' }}>{stepDelay}s</span>
        </div>
      </div>

      {/* ─── DUAL-PANE WORKSPACE ─── */}
      <div className="workspace-grid">
        {/* Left Pane: Main Operational Console */}
        <div className="main-pane">
          {/* Tabs */}
          <div className="tab-strip">
            <button
              className={`tab-item ${activeTab === 'runbook' ? 'active' : ''}`}
              onClick={() => setActiveTab('runbook')}
            >
              <Terminal size={14} />
              <span>Execution Runbook</span>
              <span className="tab-count">{eventsLog.length}</span>
            </button>

            <button
              className={`tab-item ${activeTab === 'diff' ? 'active' : ''}`}
              onClick={() => setActiveTab('diff')}
            >
              <Code2 size={14} />
              <span>AST Patch & Diff</span>
              {diffData.lines_added > 0 && (
                <span className="tab-count stat-add">+{diffData.lines_added} / -{diffData.lines_removed}</span>
              )}
            </button>

            <button
              className={`tab-item ${activeTab === 'verification' ? 'active' : ''}`}
              onClick={() => setActiveTab('verification')}
            >
              <ShieldCheck size={14} />
              <span>Verification Gate</span>
              <span className="tab-count">{isVerified ? '6/6' : '0/6'}</span>
            </button>

            <button
              className={`tab-item ${activeTab === 'postmortem' ? 'active' : ''}`}
              onClick={() => setActiveTab('postmortem')}
            >
              <FileText size={14} />
              <span>Postmortem & Audit</span>
            </button>
          </div>

          {/* Tab Content */}
          <div className="tab-content">
            {/* 1. RUNBOOK TAB */}
            {activeTab === 'runbook' && (
              <div className="runbook-container">
                {eventsLog.length === 0 ? (
                  <div className="trace-empty">
                    <Terminal size={24} style={{ opacity: 0.4 }} />
                    <p style={{ fontWeight: 500 }}>Autonomous SRE Agent Standing By</p>
                    <p style={{ fontSize: '12px' }}>
                      Click <strong>Launch Autonomous Agent</strong> above to observe the telemetry spike, isolate the failure in sandbox, synthesize the patch, and verify against regressions.
                    </p>
                  </div>
                ) : (
                  eventsLog.map((ev, index) => (
                    <div className="trace-item" key={index}>
                      <div className="trace-header">
                        <div className="trace-meta">
                          <span className="trace-step-tag">STEP {String(ev.step).padStart(2, '0')}</span>
                          <span className="trace-tool-tag">{ev.tool}</span>
                        </div>
                        <span className="trace-time">{ev.time}</span>
                      </div>
                      <div className="trace-summary">{ev.summary}</div>
                    </div>
                  ))
                )}
                <div ref={runbookEndRef} />
              </div>
            )}

            {/* 2. AST PATCH & DIFF TAB */}
            {activeTab === 'diff' && (
              <div className="card">
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <GitCommit size={14} color="var(--color-primary)" />
                    <span>Targeted Minimal Patch — {currentScenario.primary_file}</span>
                  </div>
                  {diffData.lines_added > 0 && (
                    <div className="diff-stats-pill">
                      <span className="stat-add">+{diffData.lines_added} lines</span>
                      <span className="stat-del">-{diffData.lines_removed} lines</span>
                    </div>
                  )}
                </div>

                <div className="card-body" style={{ padding: '0' }}>
                  <div className="diff-viewer" style={{ border: 'none', borderRadius: '0' }}>
                    <div className="diff-toolbar">
                      <span className="diff-file-path">diff --git a/{currentScenario.primary_file} b/{currentScenario.primary_file}</span>
                      <span style={{ color: 'var(--text-muted)' }}>AST Exception Boundary Fix</span>
                    </div>

                    <div className="diff-lines">
                      {diffLines.length === 0 ? (
                        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No git diff generated yet. Run the autonomous investigation to patch the repository.
                        </div>
                      ) : (
                        diffLines.map((line, idx) => {
                          let type = 'context';
                          if (line.startsWith('+') && !line.startsWith('+++')) type = 'add';
                          else if (line.startsWith('-') && !line.startsWith('---')) type = 'del';
                          else if (line.startsWith('@@')) type = 'hunk';

                          return (
                            <div className={`diff-row ${type}`} key={idx}>
                              <span className="diff-gutter">
                                {type === 'add' ? '+' : type === 'del' ? '-' : ' '}
                              </span>
                              <span className="diff-content">{line.slice(1) || ' '}</span>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>

                <div style={{ padding: '14px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-surface)' }}>
                  <div style={{ fontWeight: 600, fontSize: '12px', marginBottom: '4px' }}>Why Existing Tests Missed This Regression</div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '11px', lineHeight: '1.5' }}>
                    Deployment v2.4.1 refactored the checkout endpoint to handle unknown exceptions via a generic <code>except Exception:</code> block.
                    Existing tests validated valid discount vouchers, but did not exercise expired coupons against the complete HTTP serialization pipeline.
                  </p>
                </div>
              </div>
            )}

            {/* 3. VERIFICATION GATE TAB */}
            {activeTab === 'verification' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="card">
                    <div className="card-header" style={{ color: 'var(--color-rose)' }}>
                      <span>PRE-PATCH BEHAVIOR (v2.4.1)</span>
                    </div>
                    <div className="card-body mono" style={{ fontSize: '11px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>POST /v1/checkout {"{"}"coupon": "EXPIRED_SAVE20"{"}"}</div>
                      <div style={{ padding: '8px', background: 'var(--bg-app)', border: '1px solid var(--color-rose-border)', borderRadius: '4px', color: 'var(--color-rose)' }}>
                        HTTP 500 Internal Error
                        <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>{"{"}"error": "Internal Error", "status": 500{"}"}</div>
                      </div>
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header" style={{ color: 'var(--color-emerald)' }}>
                      <span>POST-PATCH BEHAVIOR (VERIFIED)</span>
                    </div>
                    <div className="card-body mono" style={{ fontSize: '11px' }}>
                      <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>POST /v1/checkout {"{"}"coupon": "EXPIRED_SAVE20"{"}"}</div>
                      <div style={{ padding: '8px', background: 'var(--bg-app)', border: '1px solid var(--color-emerald-border)', borderRadius: '4px', color: 'var(--color-emerald)' }}>
                        HTTP 400 Bad Request
                        <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>{"{"}"error": "Coupon EXPIRED_SAVE20 is expired", "status": 400{"}"}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <span>Adversarial Safety Checks</span>
                    <span className="badge badge-service">GATE STATUS: {isVerified ? 'PASSED' : 'PENDING'}</span>
                  </div>
                  <div className="card-body" style={{ padding: '10px' }}>
                    <div className="verify-grid">
                      {[
                        { title: 'Incident Vector Falsification', desc: 'Expired coupon returns HTTP 400 instead of HTTP 500.', pass: isVerified },
                        { title: 'Full Regression Suite', desc: '11 baseline unit tests executed in sandbox with zero failures.', pass: isVerified },
                        { title: 'Exception Boundary Preservation', desc: 'Unhandled internal exceptions correctly bubble as HTTP 500.', pass: isVerified },
                        { title: 'Response Contract Compliance', desc: 'Error payload schema matches OpenAPI specification.', pass: isVerified },
                        { title: 'Discount Calculation Invariant', desc: 'Active coupons (SAVE10, WELCOME20) calculate exact deductions.', pass: isVerified },
                        { title: 'Blast Radius Containment', desc: 'Only app/checkout.py modified. No shared library dependencies touched.', pass: isVerified }
                      ].map((chk, i) => (
                        <div className="verify-row" key={i}>
                          <div className="verify-icon">
                            {chk.pass ? <CheckCircle2 size={15} color="var(--color-emerald)" /> : <AlertTriangle size={15} color="var(--text-muted)" />}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div className="verify-title">{chk.title}</div>
                            <div className="verify-desc">{chk.desc}</div>
                          </div>
                          <span className={`badge ${chk.pass ? 'badge-service' : ''}`} style={{ color: chk.pass ? 'var(--color-emerald)' : 'var(--text-muted)' }}>
                            {chk.pass ? 'PASSED' : 'PENDING'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 4. POSTMORTEM TAB */}
            {activeTab === 'postmortem' && (
              <div className="postmortem-container">
                <div className="card">
                  <div className="card-header">
                    <span>Human Review & Merge Gate</span>
                    {humanApproved ? (
                      <span className="badge" style={{ color: 'var(--color-emerald)', background: 'var(--color-emerald-subtle)', border: '1px solid var(--color-emerald-border)' }}>
                        <Check size={11} /> APPROVED FOR MERGE
                      </span>
                    ) : (
                      <span className="badge badge-sev1">APPROVAL REQUIRED</span>
                    )}
                  </div>
                  <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '13px', marginBottom: '2px' }}>
                        {humanApproved ? 'Patch Signed Off by Engineer' : 'Awaiting SRE Review'}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                        {humanApproved
                          ? 'Audit trail recorded. Pull request created for continuous deployment staging pipeline.'
                          : 'Review the verified diff, test outputs, and causal evidence before signing off for production release.'}
                      </div>
                    </div>
                    <button
                      className={`btn ${humanApproved ? 'btn-secondary' : 'btn-success'}`}
                      onClick={handleApprove}
                      disabled={humanApproved}
                    >
                      {humanApproved ? <><Check size={13} /> Approved</> : <><Lock size={13} /> Sign Off Patch</>}
                    </button>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <span>Incident Postmortem — RFC-compliant</span>
                    <div className="card-header-actions">
                      <button
                        className="btn btn-secondary"
                        style={{ height: '24px', fontSize: '11px', padding: '0 8px' }}
                        onClick={() => copyPostmortem(artifacts[`incident_${selectedIncident}.md`] || '')}
                      >
                        <Copy size={11} />
                        <span>{copiedPostmortem ? 'Copied!' : 'Copy Markdown'}</span>
                      </button>
                      {artifacts[`incident_${selectedIncident}.md`] && (
                        <a
                          className="btn btn-secondary"
                          style={{ height: '24px', fontSize: '11px', padding: '0 8px' }}
                          href={`data:text/markdown;charset=utf-8,${encodeURIComponent(artifacts[`incident_${selectedIncident}.md`])}`}
                          download={`incident_${selectedIncident}.md`}
                        >
                          <Download size={11} />
                          <span>Export .md</span>
                        </a>
                      )}
                    </div>
                  </div>
                  <div className="card-body" style={{ padding: '0' }}>
                    <div className="markdown-preview">
                      {artifacts[`incident_${selectedIncident}.md`] || `### Incident ${selectedIncident} Postmortem\n\nRun autonomous investigation to generate the complete audit bundle, including 5 Whys, blast radius analysis, and regression prevention rules.`}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Telemetry & Hypotheses HUD */}
        <div className="hud-pane">
          {/* Card 1: Telemetry Spike */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={13} color="var(--color-rose)" />
                <span>Error Rate % (5m Buckets)</span>
              </div>
              <span className="mono" style={{ color: 'var(--color-rose)', fontSize: '11px' }}>Peak: {currentScenario.error_rate_after}</span>
            </div>
            <div className="card-body">
              <div className="chart-container">
                {errorSeries.map((rate, idx) => (
                  <div className="spark-col" key={idx}>
                    <div
                      className={`spark-bar ${rate > 5 ? 'danger' : 'normal'}`}
                      style={{ height: `${(rate / maxErr) * 100}%` }}
                      title={`${rate}% error rate`}
                    />
                    <span className="spark-label">{rate > 9 ? Math.round(rate) : rate}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)', marginTop: '8px' }}>
                <span>Baseline: ~0.8%</span>
                <span style={{ color: 'var(--color-rose)' }}>v2.4.1 Deploy Spike</span>
              </div>
            </div>
          </div>

          {/* Card 2: Bayesian Hypotheses Matrix */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <GitBranch size={13} color="var(--color-primary)" />
                <span>Multi-Hypothesis Evaluation</span>
              </div>
            </div>
            <div className="card-body" style={{ padding: '0' }}>
              <table className="hypo-table">
                <thead>
                  <tr>
                    <th>Hypothesis</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <div style={{ fontWeight: 600 }}>H1: Coupon Error Catch-all</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>checkout.py:28 AppError swallowed</div>
                    </td>
                    <td>
                      <span className="hypo-status-badge hypo-status-confirmed">CONFIRMED</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="confidence-track">
                        <div className="confidence-fill" style={{ width: '97%', background: 'var(--color-emerald)' }} />
                      </div>
                      <span className="mono" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-emerald)' }}>97%</span>
                    </td>
                  </tr>

                  <tr>
                    <td>
                      <div style={{ fontWeight: 600 }}>H2: DB Pool Exhaustion</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Pool utilization 3/20 normal</div>
                    </td>
                    <td>
                      <span className="hypo-status-badge hypo-status-rejected">DISPROVEN</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="confidence-track">
                        <div className="confidence-fill" style={{ width: '2%', background: 'var(--color-rose)' }} />
                      </div>
                      <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>2%</span>
                    </td>
                  </tr>

                  <tr>
                    <td>
                      <div style={{ fontWeight: 600 }}>H3: Payment Gateway Timeout</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Provider status 100% healthy</div>
                    </td>
                    <td>
                      <span className="hypo-status-badge hypo-status-rejected">DISPROVEN</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="confidence-track">
                        <div className="confidence-fill" style={{ width: '1%', background: 'var(--color-rose)' }} />
                      </div>
                      <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>1%</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Card 3: Live Log Explorer */}
          <div className="card" style={{ flex: 1, minHeight: '220px', display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Search size={13} color="var(--text-muted)" />
                <span>Production Log Filter</span>
              </div>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && fetchTelemetry()}
                  placeholder="Grep pattern (e.g. CouponExpired)..."
                  className="scenario-dropdown"
                  style={{ flex: 1, height: '28px', fontSize: '11px' }}
                />
                <button
                  className="btn btn-secondary"
                  style={{ height: '28px', padding: '0 8px', fontSize: '11px' }}
                  onClick={fetchTelemetry}
                >
                  Grep
                </button>
              </div>

              <div style={{ background: 'var(--bg-app)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '8px', flex: 1, overflowY: 'auto', maxHeight: '200px' }}>
                {searchResults.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', padding: '12px' }}>
                    No matching traces found.
                  </div>
                ) : (
                  searchResults.slice(0, 8).map((log, i) => (
                    <div key={i} style={{ marginBottom: '6px', fontSize: '10px', fontFamily: 'Geist Mono', lineHeight: '1.4' }}>
                      <span style={{ color: 'var(--color-primary)' }}>{log.file}:{log.line_number}</span>
                      <div style={{ color: log.text.includes('ERROR') ? 'var(--color-rose)' : 'var(--text-secondary)' }}>
                        {log.text}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
