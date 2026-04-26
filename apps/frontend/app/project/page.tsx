'use client';

import React, { useEffect, useState } from 'react';
import { fetchProjectState } from '../../lib/api';
import type { ProjectState } from '../../lib/api';

export default function ProjectPage() {
  const [project, setProject] = useState<ProjectState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjectState()
      .then(setProject)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  if (!project) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Loading...</div>;
  }

  const levels: { label: string; key: string; color: string }[] = [
    { label: 'L1', key: 'L1', color: '#22c55e' },
    { label: 'L2', key: 'L2', color: '#3b82f6' },
    { label: 'L3', key: 'L3', color: '#f59e0b' },
    { label: 'L4', key: 'L4', color: '#8b5cf6' },
  ];

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Current Project
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Project configuration and status
      </p>

      {/* Phase Display */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        marginBottom: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 20px', color: '#1f2937' }}>
          Level Progression
        </h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {levels.map((level, index) => {
            const isActive = project.current_level === level.key;
            const isPast = levels.findIndex((l) => l.key === project.current_level) > index;
            return (
              <React.Fragment key={level.key}>
                <div style={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  backgroundColor: isActive ? level.color : isPast ? '#d1fae5' : '#f3f4f6',
                  color: isActive ? '#fff' : isPast ? '#166534' : '#9ca3af',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: 18,
                  border: isActive ? `3px solid ${level.color}` : '2px solid #e5e7eb',
                  boxShadow: isActive ? `0 0 0 4px ${level.color}30` : 'none',
                  transition: 'all 0.2s ease',
                }}>
                  {isPast ? '✓' : level.label}
                </div>
                {index < levels.length - 1 && (
                  <div style={{
                    flex: 1,
                    height: 3,
                    backgroundColor: isPast ? '#d1fae5' : '#e5e7eb',
                    borderRadius: 2,
                  }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
        <p style={{ fontSize: 13, color: '#666', marginTop: 16, textAlign: 'center' }}>
          Current: <strong style={{ color: '#1a1a2e' }}>L{project.current_level}</strong> — {project.phase}
        </p>
      </div>

      {/* Project Info */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        marginBottom: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
          Project Information
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 }}>
          <InfoRow label="Version" value={project.version} />
          <InfoRow label="Phase" value={project.phase} />
          <InfoRow label="Status" value={project.status} />
          <InfoRow label="Current Level" value={project.current_level} />
          <InfoRow label="Last Updated" value={new Date(project.last_updated).toLocaleString()} />
        </div>
      </div>

      {/* Config */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
          Configuration Parameters
        </h2>
        {project.config && Object.keys(project.config).length > 0 ? (
          <pre style={{
            backgroundColor: '#f9fafb',
            padding: 16,
            borderRadius: 8,
            fontSize: 13,
            overflow: 'auto',
            maxHeight: 400,
            color: '#4b5563',
          }}>
            {JSON.stringify(project.config, null, 2)}
          </pre>
        ) : (
          <div style={{ color: '#9ca3af', fontSize: 14 }}>No configuration parameters available.</div>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid #f3f4f6' }}>
      <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#1f2937' }}>
        {value}
      </div>
    </div>
  );
}
