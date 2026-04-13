import { useState, useEffect, useCallback } from 'react';
import { Server, ExternalLink, Square, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getHubBaseUrl, getUsername } from '@/lib/api-base';

export function ServerStatus() {
  const [active, setActive] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const username = getUsername();
  const hubBase = getHubBaseUrl();
  const serverUrl = `${hubBase}user/${username}/`;

  useEffect(() => {
    const check = () => {
      fetch(`${hubBase}api/users/${username}`, { headers: { Accept: 'application/json' } })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => { if (data) setActive(Boolean(data.server)); setLoaded(true); })
        .catch(() => setLoaded(true));
    };
    check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, [hubBase, username]);

  const handleStop = useCallback(async () => {
    setStopping(true);
    try {
      const resp = await fetch(`${hubBase}api/users/${username}/server`, { method: 'DELETE' });
      if (resp.ok || resp.status === 204 || resp.status === 202) setActive(false);
    } catch { /* ignore */ }
    finally { setStopping(false); }
  }, [hubBase, username]);

  if (!loaded) return null;

  return (
    <div className="w-full flex items-center gap-3 rounded-xl border border-border/50 bg-white/60 dark:bg-slate-800/60 backdrop-blur-sm px-4 py-3">
      <div className={cn(
        'size-9 rounded-lg flex items-center justify-center text-white shrink-0',
        active ? 'bg-emerald-500' : 'bg-slate-400 dark:bg-slate-600',
      )}>
        <Server className="size-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground/90">My Server</span>
          <span className={cn(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold',
            active
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
              : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
          )}>
            <span className={cn('size-1.5 rounded-full', active ? 'bg-emerald-500' : 'bg-slate-400')} />
            {active ? 'Running' : 'Stopped'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground/60 mt-0.5">
          {active ? 'Your JupyterLab notebook server is running' : 'Choose a course to start learning'}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {active && (
          <>
            <button onClick={handleStop} disabled={stopping}
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 dark:border-red-800/40 bg-red-50 dark:bg-red-900/20 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors disabled:opacity-50">
              {stopping ? <Loader2 className="size-3 animate-spin" /> : <Square className="size-3" />}
              {stopping ? 'Stopping...' : 'Stop'}
            </button>
            <a href={serverUrl}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity">
              <ExternalLink className="size-3" /> Open
            </a>
          </>
        )}
      </div>
    </div>
  );
}
