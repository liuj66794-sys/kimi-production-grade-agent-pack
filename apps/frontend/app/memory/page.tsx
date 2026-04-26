'use client';

import React, { useEffect, useState } from 'react';
import { fetchMemoryCandidates } from '../../lib/api';
import type { MemoryCandidate } from '../../lib/api';

export default function MemoryPage() {
  const [candidates, setCandidates] = useState<MemoryCandidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');

  useEffect(() => {
    fetchMemoryCandidates()
      .then(setCandidates)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  const filtered = filter === 'all' ? candidates : candidates.filter((c) => c.review_status === filter);

  const riskColors: Record<string, string> = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
  };

  const statusColors: Record<string, { bg: string; color: string }> = {
    pending: { bg: '#fef3c7', color: '#92400e' },
    approved: { bg: '#d1fae5', color: '#166534' },
    rejected: { bg: '#fee2e2', color: '#991b1b' },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
            Memory Review
          </h1>
          <p style={{ color: '#888', fontSize: 14 }}>
            Read-only view of memory candidates
          </p>
        </div>
        <div style={{
          padding: '8px 16px',
          backgroundColor: '#fef3c7',
          borderRadius: 8,
          fontSize: 12,
          color: '#92400e',
          fontWeight: 600,
          border: '1px solid #fcd34d',
        }}>
          ⚠️ Read-Only: Approve/Reject via API only
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: 8,
        marginBottom: 20,
        flexWrap: 'wrap',
      }}>
        {(['all', 'pending', 'approved', 'rejected'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: 'none',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: filter === f ? 600 : 400,
              backgroundColor: filter === f ? '#1a1a2e' : '#f3f4f6',
              color: filter === f ? '#fff' : '#4b5563',
              transition: 'all 0.15s ease',
              textTransform: 'capitalize',
            }}
          >
            {f} ({f === 'all' ? candidates.length : candidates.filter((c) => c.review_status === f).length})
          </button>
        ))}
      </div>

      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
            {candidates.length === 0 ? 'No memory candidates found.' : 'No candidates match the selected filter.'}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Source</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Content</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Confidence</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Risk</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((candidate) => (
                  <tr key={candidate.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500, color: '#1f2937', whiteSpace: 'nowrap' }}>
                      {candidate.source}
                    </td>
                    <td style={{
                      padding: '10px 12px',
                      color: '#4b5563',
                      maxWidth: 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {candidate.content}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 60,
                          height: 6,
                          backgroundColor: '#f3f4f6',
                          borderRadius: 3,
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${Math.round(candidate.confidence * 100)}%`,
                            height: '100%',
                            backgroundColor: candidate.confidence >= 0.8 ? '#22c55e' : candidate.confidence >= 0.5 ? '#f59e0b' : '#ef4444',
                            borderRadius: 3,
                          }} />
                        </div>
                        <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#6b7280' }}>
                          {(candidate.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 700,
                        backgroundColor: (riskColors[candidate.risk] || '#6b7280') + '15',
                        color: riskColors[candidate.risk] || '#6b7280',
                        textTransform: 'uppercase',
                      }}>
                        {candidate.risk}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 700,
                        backgroundColor: statusColors[candidate.review_status]?.bg || '#f3f4f6',
                        color: statusColors[candidate.review_status]?.color || '#6b7280',
                        textTransform: 'uppercase',
                      }}>
                        {candidate.review_status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#9ca3af', whiteSpace: 'nowrap' }}>
                      {new Date(candidate.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{
        marginTop: 24,
        padding: 16,
        backgroundColor: '#f9fafb',
        borderRadius: 8,
        fontSize: 13,
        color: '#6b7280',
        border: '1px solid #e5e7eb',
      }}>
        <strong>Note:</strong> This UI is read-only. Memory candidates must be approved or rejected via the backend API.
        Use <code style={{ backgroundColor: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>POST /api/memory-candidates/&#123;id&#125;/approve</code> or
        <code style={{ backgroundColor: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>POST /api/memory-candidates/&#123;id&#125;/reject</code>.
      </div>
    </div>
  );
}
