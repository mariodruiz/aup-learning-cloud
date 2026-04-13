import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { nanoid } from 'nanoid';
import { CoursePage } from '@/components/auplc/course-page';
import { SettingsDialog } from '@/components/settings';
import { useTheme } from '@/lib/hooks/use-theme';
import '@/styles/codelab.css';

const jhdata = window.jhdata ?? { base_url: '/hub/', xsrf_token: '', user: 'student' };
const baseUrl = jhdata.base_url ?? '/hub/';

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function HomePage() {
  const navigate = useNavigate();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [serverActive, setServerActive] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [genInput, setGenInput] = useState('');
  const [genLang, setGenLang] = useState<'zh-CN' | 'en-US'>('en-US');
  const [settingsOpen, setSettingsOpen] = useState(false);

  const serverUrl = `${baseUrl.replace(/\/?$/, '/')}user/${jhdata.user ?? 'student'}/`;

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  useEffect(() => {
    const poll = () => {
      fetch(`${baseUrl}api/users/${jhdata.user ?? 'student'}`, { headers: { Accept: 'application/json' } })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => { if (data) setServerActive(Boolean(data.server)); })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 15_000);
    return () => clearInterval(id);
  }, []);

  const handleStopClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (stopping) return;
    setShowStopConfirm(true);
  }, [stopping]);

  const doStop = useCallback(async () => {
    setShowStopConfirm(false);
    setStopping(true);
    setStopError(null);
    try {
      const resp = await fetch(`${baseUrl}api/users/${jhdata.user}/server`, {
        method: 'DELETE',
        headers: { 'X-XSRFToken': jhdata.xsrf_token ?? '' },
      });
      if (resp.ok || resp.status === 204 || resp.status === 202) setServerActive(false);
      else setStopError(`Failed to stop server (HTTP ${resp.status})`);
    } catch { setStopError('Network error'); }
    finally { setStopping(false); }
  }, []);

  const handleGenerate = () => {
    if (!genInput.trim()) return;
    const sessionState = {
      sessionId: nanoid(),
      requirements: { requirement: genInput, language: genLang },
      pdfText: '',
      pdfImages: [],
      imageStorageIds: [],
      sceneOutlines: null,
      currentStep: 'generating' as const,
    };
    sessionStorage.setItem('generationSession', JSON.stringify(sessionState));
    navigate('/generation-preview');
  };

  return (
    <div className="home-page">
      {/* Hero — identical to Code Lab */}
      <section className="home-hero">
        <div className="container" style={{ position: 'relative' }}>
          <nav className="hero-nav">
            <a href={`${baseUrl}spawn`}><i className="fa fa-rocket"></i> Launch Server</a>
            {Boolean((jhdata as Record<string, unknown>).admin) && (
              <a href={`${baseUrl}admin/users`}><i className="fa fa-cog"></i> Admin</a>
            )}
            <button className="hero-nav-btn" onClick={() => setSettingsOpen(true)} title="AI Settings">
              <i className="fa fa-sliders"></i> AI Settings
            </button>
            <button className="theme-toggle" onClick={toggleTheme} title={resolvedTheme === 'light' ? 'Dark mode' : 'Light mode'}>
              <i className={`fa ${resolvedTheme === 'light' ? 'fa-moon-o' : 'fa-sun-o'}`}></i>
            </button>
          </nav>
          <p className="hero-greeting">{getGreeting()}, {jhdata.user ?? 'student'}</p>
          <h1>Welcome to <span className="accent">AUP Learning Cloud</span></h1>
          <p className="hero-desc">
            AI-powered learning with AMD ROCm GPU acceleration.
            Generate interactive classrooms, get course recommendations,
            and launch hands-on Jupyter notebooks.
          </p>
        </div>
      </section>

      {/* Launch Bar — identical to Code Lab */}
      <div className="container">
        <div className="launch-bar">
          <div className={`lb-icon ${serverActive ? 'running' : 'stopped'}`}>
            <i className="fa fa-server"></i>
          </div>
          <div className="lb-info">
            <div className="lb-title">
              My Server
              {serverActive ? (
                <span className="status-badge running"><span className="status-dot running"></span> Running</span>
              ) : (
                <span className="status-badge stopped"><span className="status-dot stopped"></span> Stopped</span>
              )}
            </div>
            <div className="lb-desc">
              {stopError ? (
                <span className="lb-error">{stopError}</span>
              ) : stopping ? 'Stopping your server\u2026'
                : serverActive ? 'Your server is running \u2014 click "My Server" to open JupyterLab'
                : 'Choose a course below or generate an AI classroom'}
            </div>
          </div>
          <div className="lb-actions">
            {serverActive ? (
              <>
                <a role="button" className={`btn-home-sm danger${stopping ? ' disabled' : ''}`} onClick={handleStopClick}>
                  <i className={`fa ${stopping ? 'fa-spinner fa-spin' : 'fa-stop'}`}></i>{' '}
                  {stopping ? 'Stopping\u2026' : 'Stop My Server'}
                </a>
                <a role="button" className={`btn-launch${stopping ? ' disabled' : ''}`} href={stopping ? undefined : serverUrl}>
                  <i className={`fa ${stopping ? 'fa-spinner fa-spin' : 'fa-external-link'}`}></i>
                  {stopping ? ' Stopping\u2026' : ' My Server'}
                </a>
              </>
            ) : (
              <a role="button" className="btn-launch" href={`${baseUrl}spawn`}>
                <i className="fa fa-play"></i> Start My Server
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Quick Start — identical to Code Lab */}
      <div className="container">
        <section className="home-section" style={{ paddingBottom: '0.5rem' }}>
          <div className="qs-strip">
            <div className="qs-step">
              <div className="qs-num">1</div>
              <div className="qs-step-text">
                <h4>Choose a Course</h4>
                <p>Pick a course below or generate an AI classroom</p>
              </div>
            </div>
            <div className="qs-step">
              <div className="qs-num">2</div>
              <div className="qs-step-text">
                <h4>AI-Guided Learning</h4>
                <p>AI generates personalized slides and quizzes</p>
              </div>
            </div>
            <div className="qs-step">
              <div className="qs-num">3</div>
              <div className="qs-step-text">
                <h4>Hands-on Lab</h4>
                <p>Launch JupyterLab and practice with AMD GPUs</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* AI Classroom Generator */}
      <div className="container">
        <section className="home-section">
          <div className="home-section-header">
            <h2>Generate AI Classroom</h2>
          </div>
          <div className="gen-card">
            <textarea
              className="gen-textarea"
              placeholder="Enter any topic and AI will create an interactive classroom with slides, quizzes, and AI teachers...&#10;&#10;e.g. &quot;Teach me about Convolutional Neural Networks for computer vision&quot;"
              rows={3}
              value={genInput}
              onChange={(e) => setGenInput(e.target.value)}
              onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleGenerate(); }}
            />
            <div className="gen-actions">
              <select className="gen-select" value={genLang} onChange={(e) => setGenLang(e.target.value as 'zh-CN' | 'en-US')}>
                <option value="en-US">English</option>
                <option value="zh-CN">Chinese</option>
              </select>
              <a role="button" className={`btn-launch${!genInput.trim() ? ' disabled' : ''}`} onClick={handleGenerate}>
                <i className="fa fa-magic"></i> Generate AI Classroom
              </a>
            </div>
          </div>
        </section>
      </div>

      {/* AI-Guided Courses — replaces "Available Resources" */}
      <div className="container">
        <section className="home-section">
          <CoursePage />
        </section>
      </div>

      {/* Footer */}
      <div className="home-footer">
        <div className="container">
          &copy; 2025–2026 Advanced Micro Devices, Inc. All rights reserved. &middot; AUP Learning Cloud
        </div>
      </div>

      {/* Settings Dialog (LLM provider, TTS, etc.) */}
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      {/* Stop Confirm Modal */}
      {showStopConfirm && (
        <div className="confirm-overlay" onClick={() => setShowStopConfirm(false)}>
          <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="confirm-icon"><i className="fa fa-exclamation-triangle"></i></div>
            <h3>Stop Server?</h3>
            <p>Any unsaved work in your notebooks may be lost.</p>
            <div className="confirm-actions">
              <button className="btn-home-sm" onClick={() => setShowStopConfirm(false)}>Cancel</button>
              <button className="btn-home-sm danger" onClick={doStop}><i className="fa fa-stop"></i> Stop Server</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
