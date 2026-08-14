export interface PatchSummary {
  id: string;
  iteration_number: number;
  test_passed: boolean | null;
  diff_preview: string;
  created_at: string;
}

export interface RunListItem {
  id: string;
  issue_url: string;
  repo_url: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'error';
  state: 'READ_ISSUE' | 'LOCATE_CODE' | 'GENERATE_PATCH' | 'RUN_TESTS' | 'OPEN_PR' | 'ESCALATE' | 'DONE';
  iteration_count: number;
  total_cost: number;
  total_latency: number;
  created_at: string;
  updated_at: string | null;
}

export interface RunDetail extends RunListItem {
  pr_url: string | null;
  error_message: string | null;
  patches: PatchSummary[];
}

export interface RunListResponse {
  items: RunListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunCreatePayload {
  issue_url: string;
  repo_url: string;
}

export interface EvalTask {
  id: string;
  repo: string;
  difficulty: 'easy' | 'medium' | 'hard';
  issue_text_preview: string;
}

export interface EvalTaskDetail {
  id: string;
  repo: string;
  commit_sha: string;
  issue_text: string;
  test_command: string;
  difficulty: string;
}

export interface EvalResultItem {
  task_id: string;
  resolved: boolean;
  iterations: number;
  cost_usd: number;
  latency_s: number;
  error: string | null;
}

export interface EvalReport {
  resolve_rate: number;
  total_cost_usd: number;
  avg_latency_s: number;
  avg_iterations: number;
  total_tasks: number;
  resolved_tasks: number;
  results: EvalResultItem[];
}

const API_BASE = '/api';

export async function fetchRuns(page = 1, pageSize = 20, status?: string): Promise<RunListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) params.set('status', status);
  const res = await fetch(`${API_BASE}/runs/?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.statusText}`);
  return res.json();
}

export async function fetchRunDetail(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run detail: ${res.statusText}`);
  return res.json();
}

export async function createRun(payload: RunCreatePayload): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || 'Failed to create run');
  }
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete run: ${res.statusText}`);
  }
}

export async function fetchEvalTasks(): Promise<{ tasks: EvalTask[] }> {
  const res = await fetch(`${API_BASE}/eval/tasks`);
  if (!res.ok) throw new Error(`Failed to fetch eval tasks: ${res.statusText}`);
  return res.json();
}

export async function runEvalBenchmark(taskIds?: string[]): Promise<EvalReport> {
  const url = taskIds && taskIds.length > 0 
    ? `${API_BASE}/eval/run?${taskIds.map(id => `task_ids=${encodeURIComponent(id)}`).join('&')}`
    : `${API_BASE}/eval/run`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to execute eval benchmark: ${res.statusText}`);
  return res.json();
}
