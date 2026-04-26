const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function safeFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ─── Project ───────────────────────────────────────────

export interface ProjectState {
  version: string;
  phase: string;
  status: string;
  current_level: string;
  config: Record<string, any>;
  last_updated: string;
}

export async function fetchProjectState(): Promise<ProjectState> {
  return safeFetch<ProjectState>(`${API_BASE}/api/project-state`);
}

// ─── Run ───────────────────────────────────────────────

export interface RunState {
  status: 'idle' | 'running' | 'blocked' | 'completed' | 'failed';
  current_step: string;
  total_steps: number;
  completed_steps: number;
  logs: string[];
  start_time: string | null;
  end_time: string | null;
}

export async function fetchRunState(): Promise<RunState> {
  return safeFetch<RunState>(`${API_BASE}/api/run-state`);
}

export async function startRun(): Promise<{ message: string }> {
  return safeFetch<{ message: string }>(`${API_BASE}/api/run/start`, { method: 'POST' });
}

export async function pauseRun(): Promise<{ message: string }> {
  return safeFetch<{ message: string }>(`${API_BASE}/api/run/pause`, { method: 'POST' });
}

export async function resumeRun(): Promise<{ message: string }> {
  return safeFetch<{ message: string }>(`${API_BASE}/api/run/resume`, { method: 'POST' });
}

// ─── Task Board ────────────────────────────────────────

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'running' | 'blocked' | 'done';
  priority: 'low' | 'medium' | 'high';
  assignee: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
}

export interface TaskBoard {
  columns: {
    todo: Task[];
    running: Task[];
    blocked: Task[];
    done: Task[];
  };
}

export async function fetchTaskBoard(): Promise<TaskBoard> {
  return safeFetch<TaskBoard>(`${API_BASE}/api/task-board`);
}

// ─── Artifacts ─────────────────────────────────────────

export interface Artifact {
  id: string;
  name: string;
  type: 'report' | 'ppt' | 'spreadsheet' | 'code' | 'image' | 'other';
  path: string;
  size: number;
  created_at: string;
  download_url: string;
}

export async function fetchRecentArtifacts(limit = 20): Promise<Artifact[]> {
  return safeFetch<Artifact[]>(`${API_BASE}/api/recent-artifacts?limit=${limit}`);
}

// ─── Agents ────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  level: 'L1' | 'L2' | 'L3' | 'L4';
  enabled: boolean;
  tools: string[];
  description: string;
}

export async function fetchAgents(): Promise<Agent[]> {
  return safeFetch<Agent[]>(`${API_BASE}/api/agents`);
}

// ─── Skills ────────────────────────────────────────────

export interface Skill {
  id: string;
  name: string;
  type: string;
  description: string;
  available: boolean;
}

export async function fetchSkills(): Promise<Skill[]> {
  return safeFetch<Skill[]>(`${API_BASE}/api/skills`);
}

// ─── Eval ──────────────────────────────────────────────

export interface EvalResult {
  id: string;
  name: string;
  type: 'smoke' | 'unit-smoke' | 'integration-smoke' | 'regression';
  status: 'pass' | 'fail' | 'skip' | 'error';
  duration: number;
  run_at: string;
  details: Record<string, any>;
}

export async function fetchEvalResults(): Promise<EvalResult[]> {
  return safeFetch<EvalResult[]>(`${API_BASE}/api/eval-results`);
}

// ─── Memory ────────────────────────────────────────────

export interface MemoryCandidate {
  id: string;
  source: string;
  content: string;
  confidence: number;
  risk: 'low' | 'medium' | 'high';
  review_status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export async function fetchMemoryCandidates(): Promise<MemoryCandidate[]> {
  return safeFetch<MemoryCandidate[]>(`${API_BASE}/api/memory-candidates`);
}

// ─── Gate Status ───────────────────────────────────────

export interface GateCheck {
  name: string;
  passed: boolean;
  message: string;
}

export interface GateStatus {
  name: string;
  status: 'locked' | 'unlocked' | 'passed';
  checks: GateCheck[];
  recommendation: string;
}

export async function fetchGateStatus(): Promise<GateStatus[]> {
  return safeFetch<GateStatus[]>(`${API_BASE}/api/gate-status`);
}

// ─── Script Console ────────────────────────────────────

export interface ScriptDef {
  name: string;
  description: string;
  params: Array<{
    name: string;
    type: string;
    required: boolean;
    default?: any;
  }>;
}

export async function fetchWhitelistedScripts(): Promise<ScriptDef[]> {
  return safeFetch<ScriptDef[]>(`${API_BASE}/api/scripts/whitelist`);
}

export async function runScript(
  scriptName: string,
  params: Record<string, any> = {}
): Promise<{ job_id: number; status: string }> {
  return safeFetch<{ job_id: number; status: string }>(
    `${API_BASE}/api/jobs/run-script?script_name=${encodeURIComponent(scriptName)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }
  );
}

export interface Job {
  id: number;
  job_type: string;
  status: string;
  params: Record<string, any>;
  result: Record<string, any> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  pid: number | null;
}

export async function fetchJobHistory(limit = 20): Promise<Job[]> {
  return safeFetch<Job[]>(`${API_BASE}/api/jobs?limit=${limit}`);
}
