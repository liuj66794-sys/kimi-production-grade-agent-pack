'use client';

import React, { useEffect, useState, useRef } from 'react';
import { fetchRunState, startRun, pauseRun, resumeRun } from '../../lib/api';
import type { RunState } from '../../lib/api';

export default function RunPage() {
  const [run, setRun] = useState<RunState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const loadRun = async () => {
    try {
      const data = await fetchRunState();
      setRun(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    loadRun();
    const interval = setInterval(loadRun, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [run?.logs]);

  const handleAction = async (action: 'start' | 'pause' | 'resume') => {
    setIsLoading(true);
    setActionMsg(null);
    try {
      let result: { message: string };
      if (action === 'start') result = await startRun();
      else if (action === 'pause') result = await pauseRun();
      else result = await resumeRun();
      setActionMsg(result.message);
      await loadRun();
    } catch (e: any) {
      setActionMsg(`Error: ${e.message}`);
    } finally {
      setIsLoading(false);
      setTimeout(() => setActionMsg(null), 4000);
    }
  };

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  if (!run) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Loading...</div>;
  }

  const statusColors: Record<string, string> = {
    idle: '#6b7280',
    running: '#22c55e',
    blocked: '#f59e0b',
    completed: '#3b82f6',
    failed: '#ef4444',
  };

  const progress = run.total_steps > 0 ? (run.completed_steps / run.total_steps) * 100 : 0;

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Current Run
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Monitor and control the agent run
      </p>

      {/* Status Card */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        marginBottom: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
              Status
            </div>
            <div style={{
              fontSize: 20,
              fontWeight: 700,
              color: statusColors[run.status] || '#6b7280',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                backgroundColor: statusColors[run.status] || '#6b7280',
                display: 'inline-block',
              }} />
              {run.status.toUpperCase()}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            {run.status === 'idle' && (
              <button
                onClick={() => handleAction('start')}
                disabled={isLoading}
                style={btnStyle('#22c55e', '#fff')}
              >
                {isLoading ? '...' : '▶ Start'}
              </button>
            )}
            {run.status === 'running' && (
              <button
                onClick={() => handleAction('pause')}
                disabled={isLoading}
                style={btnStyle('#f59e0b', '#fff')}
              >
                {isLoading ? '...' : '⏸ Pause'}
              </button>
            )}
            {run.status === 'blocked' && (
              <button
                onClick={() => handleAction('resume')}
                disabled={isLoading}
                style={btnStyle('#3b82f6', '#fff')}
              >
                {isLoading ? '...' : '▶ Resume'}
              </button>
            )}
          </div>
        </div>

        {actionMsg && (
          <div style={{
            padding: '8px 14px',
            backgroundColor: actionMsg.startsWith('Error') ? '#fef2f2' : '#f0fdf4',
            color: actionMsg.startsWith('Error') ? '#ef4444' : '#166534',
            borderRadius: 8,
            fontSize: 13,
            marginBottom: 16,
          }}>
            {actionMsg}
          </div>
        )}

        {/* Progress */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 13, color: '#4b5563', fontWeight: 500 }}>
              {run.current_step || 'No active step'}
            </span>
            <span style={{ fontSize: 13, color: '#9ca3af' }}>
              {run.completed_steps} / {run.total_steps}
            </span>
          </div>
          <div style={{
            height: 10,
            backgroundColor: '#f3f4f6',
            borderRadius: 5,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${Math.min(progress, 100)}%`,
              backgroundColor: statusColors[run.status] || '#6b7280',
              borderRadius: 5,
              transition: 'width 0.5s ease',
            }} />
          </div>
        </div>

        {/* Timing */}
        <div style={{ display: 'flex', gap: 24, fontSize: 12, color: '#9ca3af' }}>
          {run.start_time && (
            <span>Started: {new Date(run.start_time).toLocaleString()}</span>
          )}
          {run.end_time && (
            <span>Ended: {new Date(run.end_time).toLocaleString()}</span>
          )}
          {run.start_time && !run.end_time && (
            <span>Duration: {Math.round((Date.now() - new Date(run.start_time).getTime()) / 1000)}s</span>
          )}
        </div>
      </div>

      {/* Logs */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: '#1f2937' }}>Run Logs</h2>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>{run.logs.length} entries</span>
        </div>

        <div style={{
          backgroundColor: '#0f172a',
          color: '#e2e8f0',
          padding: 16,
          borderRadius: 8,
          fontSize: 12,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, monospace',
          maxHeight: 400,
          overflowY: 'auto',
          lineHeight: 1.6,
        }}>
          {run.logs.length === 0 ? (
            <span style={{ color: '#475569' }}>No logs yet.</span>
          ) : (
            run.logs.map((log, i) => (
              <div key={i} style={{ marginBottom: 2 }}>
                <span style={{ color: '#64748b', marginRight: 8 }}>[{i + 1}]</span>
                {log}
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}

function btnStyle(bg: string, color: string): React.CSSProperties {
  return {
    padding: '10px 20px',
    backgroundColor: bg,
    color: color,
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'opacity 0.15s ease',
  };
}
