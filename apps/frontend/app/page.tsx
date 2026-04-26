'use client';

import React, { useEffect, useState } from 'react';
import StatusCard from '../components/StatusCard';
import { fetchProjectState, fetchRunState, fetchRecentArtifacts, fetchTaskBoard } from '../lib/api';
import type { ProjectState, RunState, Artifact, TaskBoard } from '../lib/api';

export default function HomePage() {
  const [project, setProject] = useState<ProjectState | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [taskBoard, setTaskBoard] = useState<TaskBoard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [p, r, a, t] = await Promise.all([
          fetchProjectState(),
          fetchRunState(),
          fetchRecentArtifacts(5),
          fetchTaskBoard(),
        ]);
        setProject(p);
        setRun(r);
        setArtifacts(a);
        setTaskBoard(t);
      } catch (e: any) {
        setError(e.message);
      }
    };
    load();

    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#ef4444' }}>
        <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>API Error</div>
        <div style={{ fontSize: 14 }}>{error}</div>
        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 12 }}>
          Make sure the backend API is running on the configured endpoint.
        </div>
      </div>
    );
  }

  const statusMap: Record<string, 'ok' | 'warn' | 'error' | 'info'> = {
    idle: 'info',
    running: 'ok',
    blocked: 'warn',
    completed: 'ok',
    failed: 'error',
  };

  const todoCount = taskBoard?.columns.todo.length ?? 0;
  const runningCount = taskBoard?.columns.running.length ?? 0;
  const blockedCount = taskBoard?.columns.blocked.length ?? 0;
  const doneCount = taskBoard?.columns.done.length ?? 0;

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Dashboard
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Overview of your Agent Pack project
      </p>

      {/* Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatusCard
          title="Version"
          value={project?.version ?? '---'}
          status="info"
          subtitle="L3 Frontend"
          icon="📦"
        />
        <StatusCard
          title="Phase"
          value={project?.phase ?? '---'}
          status="info"
          subtitle="Current Phase"
          icon="🔄"
        />
        <StatusCard
          title="Run Status"
          value={run?.status ?? '---'}
          status={statusMap[run?.status ?? ''] ?? 'info'}
          subtitle={run?.current_step ?? 'No active run'}
          icon="▶️"
        />
        <StatusCard
          title="Progress"
          value={run ? `${run.completed_steps}/${run.total_steps}` : '---'}
          status="ok"
          subtitle="Steps completed"
          icon="📊"
        />
        <StatusCard
          title="Tasks Todo"
          value={todoCount}
          status={todoCount > 0 ? 'warn' : 'ok'}
          subtitle={`${runningCount} running`}
          icon="📝"
        />
        <StatusCard
          title="Artifacts"
          value={artifacts.length}
          status="info"
          subtitle="Recent"
          icon="📁"
        />
      </div>

      {/* Quick Actions */}
      <div style={{ backgroundColor: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 12px', color: '#1f2937' }}>Quick Actions</h2>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <a href="/run" style={actionBtnStyle('#1a1a2e', '#fff')}>Start Run</a>
          <a href="/tasks" style={actionBtnStyle('#eff6ff', '#3b82f6')}>View Tasks</a>
          <a href="/artifacts" style={actionBtnStyle('#f0fdf4', '#16a34a')}>Browse Artifacts</a>
          <a href="/eval" style={actionBtnStyle('#fffbeb', '#d97706')}>Run Eval</a>
          <a href="/agents" style={actionBtnStyle('#faf5ff', '#9333ea')}>View Agents</a>
          <a href="/memory" style={actionBtnStyle('#fef2f2', '#dc2626')}>Review Memory</a>
        </div>
      </div>

      {/* Recent Activity */}
      <div style={{ backgroundColor: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 12px', color: '#1f2937' }}>Recent Artifacts</h2>
        {artifacts.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: 14, padding: '20px 0' }}>No artifacts yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {artifacts.map((artifact) => (
              <div
                key={artifact.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: '#f9fafb',
                  borderRadius: 8,
                  fontSize: 13,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>{artifact.type === 'report' ? '📄' : artifact.type === 'code' ? '💻' : artifact.type === 'ppt' ? '📊' : artifact.type === 'spreadsheet' ? '📈' : '📎'}</span>
                  <span style={{ fontWeight: 500, color: '#1f2937' }}>{artifact.name}</span>
                  <span style={{ fontSize: 11, color: '#9ca3af', padding: '2px 6px', backgroundColor: '#f3f4f6', borderRadius: 4 }}>
                    {artifact.type}
                  </span>
                </div>
                <span style={{ color: '#9ca3af', fontSize: 12 }}>
                  {new Date(artifact.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function actionBtnStyle(bg: string, color: string): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '8px 16px',
    backgroundColor: bg,
    color: color,
    textDecoration: 'none',
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    transition: 'opacity 0.15s ease',
    border: `1px solid ${bg === '#1a1a2e' ? '#1a1a2e' : bg}`,
  };
}
