'use client';

import React, { useEffect, useState } from 'react';
import { fetchAgents, fetchSkills } from '../../lib/api';
import type { Agent, Skill } from '../../lib/api';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchAgents().then(setAgents),
      fetchSkills().then(setSkills),
    ]).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  const levelBadge: Record<string, { bg: string; color: string }> = {
    L1: { bg: '#d1fae5', color: '#166534' },
    L2: { bg: '#dbeafe', color: '#1e40af' },
    L3: { bg: '#fef3c7', color: '#92400e' },
    L4: { bg: '#ede9fe', color: '#5b21b6' },
  };

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Agents & Skills
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Read-only view of agents and skills (L1 enabled, L2/L3 reserved)
      </p>

      {/* Level Legend */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 24,
        display: 'flex',
        gap: 20,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        fontSize: 13,
        flexWrap: 'wrap',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#22c55e' }} />
          <strong>L1</strong>: Enabled
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#3b82f6' }} />
          <strong>L2</strong>: Reserved
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#f59e0b' }} />
          <strong>L3</strong>: Reserved
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#8b5cf6' }} />
          <strong>L4</strong>: Reserved
        </span>
      </div>

      {/* Agents */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        marginBottom: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
          Agents ({agents.length})
        </h2>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Level</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Tools</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {agents.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: 30, textAlign: 'center', color: '#9ca3af' }}>
                    No agents configured.
                  </td>
                </tr>
              ) : (
                agents.map((agent) => (
                  <tr key={agent.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: '#1f2937' }}>{agent.name}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 700,
                        backgroundColor: levelBadge[agent.level]?.bg || '#f3f4f6',
                        color: levelBadge[agent.level]?.color || '#6b7280',
                      }}>
                        {agent.level}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        backgroundColor: agent.enabled ? '#d1fae5' : '#f3f4f6',
                        color: agent.enabled ? '#166534' : '#9ca3af',
                      }}>
                        {agent.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {agent.tools.map((tool) => (
                          <span key={tool} style={{
                            fontSize: 11,
                            padding: '2px 6px',
                            borderRadius: 4,
                            backgroundColor: '#f3f4f6',
                            color: '#6b7280',
                          }}>
                            {tool}
                          </span>
                        ))}
                        {agent.tools.length === 0 && (
                          <span style={{ fontSize: 11, color: '#d1d5db' }}>None</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '12px', color: '#6b7280' }}>{agent.description}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Skills */}
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
          Skills ({skills.length})
        </h2>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Type</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Available</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {skills.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: 30, textAlign: 'center', color: '#9ca3af' }}>
                    No skills configured.
                  </td>
                </tr>
              ) : (
                skills.map((skill) => (
                  <tr key={skill.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: '#1f2937' }}>{skill.name}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        backgroundColor: '#eff6ff',
                        color: '#3b82f6',
                      }}>
                        {skill.type}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        backgroundColor: skill.available ? '#d1fae5' : '#f3f4f6',
                        color: skill.available ? '#166534' : '#9ca3af',
                      }}>
                        {skill.available ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: '#6b7280' }}>{skill.description}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
