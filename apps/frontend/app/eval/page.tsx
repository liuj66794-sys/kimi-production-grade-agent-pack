'use client';

import React, { useEffect, useState } from 'react';
import { fetchEvalResults } from '../../lib/api';
import type { EvalResult } from '../../lib/api';

export default function EvalPage() {
  const [results, setResults] = useState<EvalResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvalResults()
      .then(setResults)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  const smokeTests = results.filter((r) => r.type === 'smoke');
  const unitTests = results.filter((r) => r.type === 'unit-smoke');
  const integrationTests = results.filter((r) => r.type === 'integration-smoke');
  const regressionTests = results.filter((r) => r.type === 'regression');

  const passCount = results.filter((r) => r.status === 'pass').length;
  const failCount = results.filter((r) => r.status === 'fail').length;
  const skipCount = results.filter((r) => r.status === 'skip').length;
  const errorCount = results.filter((r) => r.status === 'error').length;
  const total = results.length || 1;

  const statusColors: Record<string, string> = {
    pass: '#22c55e',
    fail: '#ef4444',
    skip: '#f59e0b',
    error: '#dc2626',
  };

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Eval Dashboard
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Evaluation and regression test results
      </p>

      {/* Summary */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 16,
        marginBottom: 32,
      }}>
        <SummaryCard label="Total" value={results.length} color="#1a1a2e" />
        <SummaryCard label="Passed" value={passCount} color="#22c55e" percentage={Math.round((passCount / total) * 100)} />
        <SummaryCard label="Failed" value={failCount} color="#ef4444" percentage={Math.round((failCount / total) * 100)} />
        <SummaryCard label="Skipped" value={skipCount} color="#f59e0b" percentage={Math.round((skipCount / total) * 100)} />
        <SummaryCard label="Errors" value={errorCount} color="#dc2626" percentage={Math.round((errorCount / total) * 100)} />
      </div>

      {/* Bar Chart */}
      {results.length > 0 && (
        <div style={{
          backgroundColor: '#fff',
          borderRadius: 12,
          padding: 24,
          marginBottom: 24,
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
            Pass/Fail Distribution
          </h2>
          <div style={{ display: 'flex', height: 32, borderRadius: 8, overflow: 'hidden' }}>
            {passCount > 0 && (
              <div style={{
                width: `${(passCount / results.length) * 100}%`,
                backgroundColor: '#22c55e',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 600,
                minWidth: passCount > 0 ? 40 : 0,
              }}>
                {passCount > 0 && `${passCount}`}
              </div>
            )}
            {failCount > 0 && (
              <div style={{
                width: `${(failCount / results.length) * 100}%`,
                backgroundColor: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 600,
                minWidth: failCount > 0 ? 40 : 0,
              }}>
                {failCount > 0 && `${failCount}`}
              </div>
            )}
            {skipCount > 0 && (
              <div style={{
                width: `${(skipCount / results.length) * 100}%`,
                backgroundColor: '#f59e0b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 600,
                minWidth: skipCount > 0 ? 40 : 0,
              }}>
                {skipCount > 0 && `${skipCount}`}
              </div>
            )}
            {errorCount > 0 && (
              <div style={{
                width: `${(errorCount / results.length) * 100}%`,
                backgroundColor: '#dc2626',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#fff',
                fontWeight: 600,
                minWidth: errorCount > 0 ? 40 : 0,
              }}>
                {errorCount > 0 && `${errorCount}`}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 12 }}>
            {passCount > 0 && <LegendItem color="#22c55e" label={`Pass (${Math.round((passCount / results.length) * 100)}%)`} />}
            {failCount > 0 && <LegendItem color="#ef4444" label={`Fail (${Math.round((failCount / results.length) * 100)}%)`} />}
            {skipCount > 0 && <LegendItem color="#f59e0b" label={`Skip (${Math.round((skipCount / results.length) * 100)}%)`} />}
            {errorCount > 0 && <LegendItem color="#dc2626" label={`Error (${Math.round((errorCount / results.length) * 100)}%)`} />}
          </div>
        </div>
      )}

      {/* Category Tables */}
      {renderCategoryTable('Smoke Tests', smokeTests, statusColors)}
      {renderCategoryTable('Unit-Smoke Tests', unitTests, statusColors)}
      {renderCategoryTable('Integration-Smoke Tests', integrationTests, statusColors)}
      {renderCategoryTable('Regression Tests', regressionTests, statusColors)}
    </div>
  );
}

function SummaryCard({ label, value, color, percentage }: { label: string; value: number; color: string; percentage?: number }) {
  return (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: 12,
      padding: 20,
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      borderLeft: `4px solid ${color}`,
    }}>
      <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1 }}>
        {value}
        {percentage !== undefined && (
          <span style={{ fontSize: 13, fontWeight: 400, color: '#9ca3af', marginLeft: 6 }}>
            {percentage}%
          </span>
        )}
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color }} />
      {label}
    </span>
  );
}

function renderCategoryTable(title: string, items: EvalResult[], statusColors: Record<string, string>) {
  if (items.length === 0) return null;

  return (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: 12,
      padding: 24,
      marginBottom: 16,
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
    }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: '#1f2937' }}>
        {title} ({items.length})
      </h2>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
              <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
              <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Duration</th>
              <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Run At</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '10px 12px', fontWeight: 500, color: '#1f2937' }}>{item.name}</td>
                <td style={{ padding: '10px 12px' }}>
                  <span style={{
                    padding: '3px 10px',
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 700,
                    backgroundColor: statusColors[item.status] + '15',
                    color: statusColors[item.status],
                    textTransform: 'uppercase',
                  }}>
                    {item.status}
                  </span>
                </td>
                <td style={{ padding: '10px 12px', color: '#6b7280', fontFamily: 'monospace' }}>
                  {item.duration.toFixed(2)}s
                </td>
                <td style={{ padding: '10px 12px', color: '#9ca3af', fontSize: 12 }}>
                  {new Date(item.run_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
