'use client';

import React, { useState } from 'react';
import type { Artifact } from '../lib/api';

interface ArtifactListProps {
  artifacts: Artifact[];
}

const typeIcons: Record<string, string> = {
  report: '📄',
  ppt: '📊',
  spreadsheet: '📈',
  code: '💻',
  image: '🖼️',
  other: '📎',
};

const typeLabels: Record<string, string> = {
  report: 'Report',
  ppt: 'PPT',
  spreadsheet: 'Spreadsheet',
  code: 'Code',
  image: 'Image',
  other: 'Other',
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ArtifactList({ artifacts }: ArtifactListProps) {
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'size'>('date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

  const filtered = typeFilter === 'all'
    ? artifacts
    : artifacts.filter((a) => a.type === typeFilter);

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortBy === 'date') cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    else if (sortBy === 'name') cmp = a.name.localeCompare(b.name);
    else if (sortBy === 'size') cmp = a.size - b.size;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const types = ['all', ...Array.from(new Set(artifacts.map((a) => a.type)))];

  return (
    <div>
      {/* Filters */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {types.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              style={{
                padding: '6px 14px',
                borderRadius: 8,
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: typeFilter === t ? 600 : 400,
                backgroundColor: typeFilter === t ? '#1a1a2e' : '#f3f4f6',
                color: typeFilter === t ? '#fff' : '#4b5563',
                transition: 'all 0.15s ease',
              }}
            >
              {t === 'all' ? 'All' : `${typeIcons[t] || '📎'} ${typeLabels[t] || t}`}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#888' }}>Sort:</span>
          {(['date', 'name', 'size'] as const).map((s) => (
            <button
              key={s}
              onClick={() => {
                if (sortBy === s) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
                else { setSortBy(s); setSortDir('desc'); }
              }}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                border: '1px solid #e5e7eb',
                cursor: 'pointer',
                fontSize: 12,
                backgroundColor: sortBy === s ? '#eff6ff' : '#fff',
                color: sortBy === s ? '#3b82f6' : '#6b7280',
              }}
            >
              {s} {sortBy === s ? (sortDir === 'asc' ? '↑' : '↓') : ''}
            </button>
          ))}
        </div>

        <span style={{ fontSize: 13, color: '#888', marginLeft: 'auto' }}>
          Showing {sorted.length} of {artifacts.length}
        </span>
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {sorted.map((artifact) => (
          <div
            key={artifact.id}
            onClick={() => setSelectedArtifact(artifact)}
            style={{
              backgroundColor: '#fff',
              borderRadius: 12,
              padding: 18,
              cursor: 'pointer',
              border: '1px solid #e5e7eb',
              transition: 'all 0.15s ease',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)';
              (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
              (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
            }}
          >
            <div style={{ fontSize: 32, marginBottom: 10, textAlign: 'center' }}>
              {typeIcons[artifact.type] || '📎'}
            </div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: '#1f2937',
                marginBottom: 6,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {artifact.name}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#9ca3af' }}>
              <span>{typeLabels[artifact.type] || artifact.type}</span>
              <span>{formatSize(artifact.size)}</span>
            </div>
            <div style={{ fontSize: 11, color: '#d1d5db', marginTop: 8 }}>
              {new Date(artifact.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>

      {sorted.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af', fontSize: 14 }}>
          No artifacts match the selected filter.
        </div>
      )}

      {/* Detail Modal */}
      {selectedArtifact && (
        <div
          onClick={() => setSelectedArtifact(null)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
            padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: '#fff',
              borderRadius: 16,
              padding: 28,
              maxWidth: 480,
              width: '100%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{ fontSize: 40, marginRight: 12 }}>{typeIcons[selectedArtifact.type] || '📎'}</div>
              <button
                onClick={() => setSelectedArtifact(null)}
                style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: '#9ca3af' }}
              >
                ×
              </button>
            </div>

            <h2 style={{ margin: '0 0 8px', fontSize: 18, color: '#1f2937', wordBreak: 'break-all' }}>
              {selectedArtifact.name}
            </h2>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <span style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                backgroundColor: '#f3f4f6', color: '#6b7280', fontWeight: 600,
              }}>
                {typeLabels[selectedArtifact.type] || selectedArtifact.type}
              </span>
              <span style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                backgroundColor: '#f0fdf4', color: '#166534', fontWeight: 600,
              }}>
                {formatSize(selectedArtifact.size)}
              </span>
            </div>

            <div style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.8 }}>
              <div><strong>ID:</strong> {selectedArtifact.id}</div>
              <div><strong>Path:</strong> <code style={{ backgroundColor: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>{selectedArtifact.path}</code></div>
              <div><strong>Created:</strong> {new Date(selectedArtifact.created_at).toLocaleString()}</div>
            </div>

            <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
              <a
                href={selectedArtifact.download_url}
                style={{
                  display: 'inline-block',
                  padding: '8px 18px',
                  backgroundColor: '#1a1a2e',
                  color: '#fff',
                  textDecoration: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  flex: 1,
                  textAlign: 'center',
                }}
              >
                Download
              </a>
              <button
                onClick={() => setSelectedArtifact(null)}
                style={{
                  padding: '8px 18px',
                  backgroundColor: '#f3f4f6',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  color: '#4b5563',
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
