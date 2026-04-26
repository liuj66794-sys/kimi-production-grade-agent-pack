'use client';

import React, { useEffect, useState } from 'react';
import ArtifactList from '../../components/ArtifactList';
import { fetchRecentArtifacts } from '../../lib/api';
import type { Artifact } from '../../lib/api';

export default function ArtifactsPage() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchRecentArtifacts(50);
        setArtifacts(data);
      } catch (e: any) {
        setError(e.message);
      }
    };
    load();
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Recent Artifacts
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Browse and download generated artifacts
      </p>

      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        {artifacts.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
            No artifacts found.
          </div>
        ) : (
          <ArtifactList artifacts={artifacts} />
        )}
      </div>
    </div>
  );
}
