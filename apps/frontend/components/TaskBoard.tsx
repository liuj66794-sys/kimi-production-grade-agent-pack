'use client';

import React, { useState } from 'react';
import type { Task } from '../lib/api';

interface TaskBoardProps {
  columns: {
    todo: Task[];
    running: Task[];
    blocked: Task[];
    done: Task[];
  };
  onTaskClick?: (task: Task) => void;
}

const columnConfig: { key: keyof TaskBoardProps['columns']; label: string; color: string; bg: string }[] = [
  { key: 'todo', label: 'To Do', color: '#6b7280', bg: '#f9fafb' },
  { key: 'running', label: 'Running', color: '#3b82f6', bg: '#eff6ff' },
  { key: 'blocked', label: 'Blocked', color: '#ef4444', bg: '#fef2f2' },
  { key: 'done', label: 'Done', color: '#22c55e', bg: '#f0fdf4' },
];

const priorityBadge: Record<string, { bg: string; color: string; label: string }> = {
  high: { bg: '#fee2e2', color: '#dc2626', label: 'H' },
  medium: { bg: '#fef3c7', color: '#d97706', label: 'M' },
  low: { bg: '#e0f2fe', color: '#0284c7', label: 'L' },
};

export default function TaskBoard({ columns, onTaskClick }: TaskBoardProps) {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    onTaskClick?.(task);
  };

  const totalCount = Object.values(columns).reduce((sum, col) => sum + col.length, 0);

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 14, color: '#666' }}>
          Total tasks: <strong>{totalCount}</strong>
        </span>
        {columnConfig.map((col) => (
          <span key={col.key} style={{ fontSize: 13, color: col.color, fontWeight: 500 }}>
            {col.label}: {columns[col.key].length}
          </span>
        ))}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 16,
        }}
      >
        {columnConfig.map((col) => (
          <div
            key={col.key}
            style={{
              backgroundColor: col.bg,
              borderRadius: 12,
              padding: 16,
              minHeight: 400,
              border: `2px solid ${col.color}20`,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 12,
              }}
            >
              <span
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: col.color,
                }}
              >
                {col.label}
              </span>
              <span
                style={{
                  backgroundColor: col.color + '20',
                  color: col.color,
                  fontSize: 12,
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 10,
                }}
              >
                {columns[col.key].length}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {columns[col.key].map((task) => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task)}
                  style={{
                    backgroundColor: '#fff',
                    borderRadius: 8,
                    padding: 12,
                    cursor: 'pointer',
                    border: '1px solid #e5e7eb',
                    transition: 'all 0.15s ease',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
                    (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
                    (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: '2px 5px',
                        borderRadius: 4,
                        backgroundColor: priorityBadge[task.priority]?.bg || '#f3f4f6',
                        color: priorityBadge[task.priority]?.color || '#6b7280',
                      }}
                    >
                      {priorityBadge[task.priority]?.label || '?'}
                    </span>
                    {task.assignee && (
                      <span style={{ fontSize: 11, color: '#888' }}>
                        @{task.assignee}
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: '#1f2937',
                      lineHeight: 1.4,
                      marginBottom: 4,
                    }}
                  >
                    {task.title}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: '#9ca3af',
                      lineHeight: 1.3,
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {task.description}
                  </div>
                  <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                    {task.tags.map((tag) => (
                      <span
                        key={tag}
                        style={{
                          fontSize: 10,
                          padding: '1px 6px',
                          borderRadius: 4,
                          backgroundColor: '#f3f4f6',
                          color: '#6b7280',
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <div
          onClick={() => setSelectedTask(null)}
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
              maxWidth: 560,
              width: '100%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 20, color: '#1f2937' }}>{selectedTask.title}</h2>
              <button
                onClick={() => setSelectedTask(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: 24,
                  cursor: 'pointer',
                  color: '#9ca3af',
                  lineHeight: 1,
                }}
              >
                ×
              </button>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              <span style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                backgroundColor: priorityBadge[selectedTask.priority]?.bg || '#f3f4f6',
                color: priorityBadge[selectedTask.priority]?.color || '#6b7280',
                fontWeight: 600,
              }}>
                Priority: {selectedTask.priority}
              </span>
              <span style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                backgroundColor: '#f3f4f6', color: '#6b7280', fontWeight: 600,
              }}>
                Status: {selectedTask.status}
              </span>
              {selectedTask.assignee && (
                <span style={{
                  fontSize: 12, padding: '4px 10px', borderRadius: 6,
                  backgroundColor: '#eff6ff', color: '#3b82f6', fontWeight: 600,
                }}>
                  @{selectedTask.assignee}
                </span>
              )}
            </div>

            <p style={{ color: '#4b5563', lineHeight: 1.6, fontSize: 14 }}>
              {selectedTask.description}
            </p>

            <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e5e7eb' }}>
              <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>
                ID: {selectedTask.id}
              </div>
              <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>
                Created: {new Date(selectedTask.created_at).toLocaleString()}
              </div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>
                Updated: {new Date(selectedTask.updated_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
