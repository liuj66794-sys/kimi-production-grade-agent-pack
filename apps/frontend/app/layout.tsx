import React from 'react';
import NavBar from '../components/NavBar';

export const metadata = {
  title: 'Kimi Agent Pack Dashboard v3.0',
  description: 'Production-Grade Agent System Dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, -apple-system, sans-serif', backgroundColor: '#f5f5f5' }}>
        <NavBar />
        <main style={{ maxWidth: 1400, margin: '0 auto', padding: '24px' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
