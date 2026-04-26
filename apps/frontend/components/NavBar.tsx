'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/project', label: 'Project' },
  { href: '/run', label: 'Run' },
  { href: '/tasks', label: 'Tasks' },
  { href: '/artifacts', label: 'Artifacts' },
  { href: '/agents', label: 'Agents' },
  { href: '/eval', label: 'Eval' },
  { href: '/memory', label: 'Memory' },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        backgroundColor: '#1a1a2e',
        color: '#fff',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      <div
        style={{
          maxWidth: 1400,
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 56,
        }}
      >
        <Link
          href="/"
          style={{
            color: '#00d4ff',
            fontSize: 18,
            fontWeight: 700,
            textDecoration: 'none',
            letterSpacing: '-0.3px',
          }}
        >
          Kimi Agent Pack
        </Link>

        <div style={{ display: 'flex', gap: 4 }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  color: isActive ? '#00d4ff' : '#b0b0c0',
                  textDecoration: 'none',
                  fontSize: 14,
                  fontWeight: isActive ? 600 : 400,
                  padding: '6px 12px',
                  borderRadius: 6,
                  backgroundColor: isActive ? 'rgba(0,212,255,0.1)' : 'transparent',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </div>

        <span
          style={{
            fontSize: 12,
            color: '#666',
            fontFamily: 'monospace',
          }}
        >
          v3.0.0
        </span>
      </div>
    </nav>
  );
}
