'use client';

import React from 'react';

interface StatusCardProps {
  title: string;
  value: string | number;
  status?: 'ok' | 'warn' | 'error' | 'info';
  subtitle?: string;
  icon?: string;
}

const statusColors: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  ok: { bg: '#f0fdf4', border: '#86efac', text: '#166534', badge: '#22c55e' },
  warn: { bg: '#fffbeb', border: '#fcd34d', text: '#92400e', badge: '#f59e0b' },
  error: { bg: '#fef2f2', border: '#fca5a5', text: '#991b1b', badge: '#ef4444' },
  info: { bg: '#eff6ff', border: '#93c5fd', text: '#1e40af', badge: '#3b82f6' },
};

export default function StatusCard({ title, value, status = 'info', subtitle, icon }: StatusCardProps) {
  const colors = statusColors[status] || statusColors.info;

  return (
    <div
      style={{
        backgroundColor: '#fff',
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
        minWidth: 180,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: '#666', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {title}
        </span>
        {icon && (
          <span style={{ fontSize: 20 }}>{icon}</span>
        )}
      </div>

      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: colors.text,
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: colors.badge,
            display: 'inline-block',
          }}
        />
        <span style={{ fontSize: 12, color: '#888' }}>
          {subtitle || status.toUpperCase()}
        </span>
      </div>
    </div>
  );
}
