'use client';

import React, { useEffect, useState } from 'react';
import TaskBoard from '../../components/TaskBoard';
import { fetchTaskBoard } from '../../lib/api';
import type { TaskBoard as TaskBoardType } from '../../lib/api';

export default function TasksPage() {
  const [board, setBoard] = useState<TaskBoardType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchTaskBoard();
        setBoard(data);
      } catch (e: any) {
        setError(e.message);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return <div style={{ color: '#ef4444', padding: 40, textAlign: 'center' }}>Error: {error}</div>;
  }

  if (!board) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>Loading tasks...</div>;
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>
        Task Board
      </h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Kanban board of all tasks
      </p>

      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 24,
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        <TaskBoard columns={board.columns} />
      </div>
    </div>
  );
}
