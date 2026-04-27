const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "/api")
  .replace(/\/+$/, "");

const LAST_AUDIT_KEY = "fairlens:lastAudit";
const USER_ID_KEY = "fairlens:userId";

export type AuditModelResult = {
  model: string;
  accuracy: number | null;
  group_approval_rates: Record<string, number>;
  disparate_impact_ratio: number | null;
  demographic_parity_difference: number | null;
  equalized_odds_difference: number | null;
  legal_pass: boolean;
  legal_threshold: string;
};

export type FairnessAudit = {
  audit_id?: string;
  user_id?: string;
  domain?: string;
  dataset_name?: string;
  target_col: string;
  sensitive_col: string;
  created_at?: string;
  status?: string;
  groups_found?: string[];
  feature_cols?: string[];
  results: AuditModelResult[];
};

export type SchemaResponse = {
  feature_cols: string[];
  target_col: string;
  sensitive_col: string;
  sensitive_groups: string[];
  domain: string;
};

export type StatusResponse = {
  trained: boolean;
  domain?: string;
  target_col?: string;
  sensitive_col?: string;
  groups?: string[];
  n_features: number;
  audit_id?: string;
};

export type DashboardGroupRow = {
  count: number;
  approval_rate: number | null;
  avg_score?: number | null;
  numeric_averages?: Record<string, number | null>;
};

export type DashboardStats = {
  by_attribute: Record<string, Record<string, DashboardGroupRow>>;
  intersectional: Record<string, { count: number; approval_rate: number | null }>;
  di_ratios: Record<string, number | null>;
  legal_flags: Record<string, "PASS" | "FAIL" | "UNKNOWN" | string>;
};

export type AuditSummary = {
  audit_id: string;
  domain: string;
  dataset_name: string;
  target_col: string;
  sensitive_col: string;
  created_at: string;
  status: string;
  models_saved: boolean;
  results_count: number;
};

export type PredictionResponse = {
  sensitive_col: string;
  sensitive_value: string;
  target_col: string;
  baseline: { decision: number; probability?: number; label: string };
  reweighted: { decision: number; label: string };
  threshold_calibrated: { decision: number; label: string };
  bias_detected: boolean;
  note: string;
};

export type CompareRequest = {
  candidate_a: Record<string, unknown>;
  candidate_b: Record<string, unknown>;
};

export type CompareResponse = {
  candidate_a_scores: PredictionResponse;
  candidate_b_scores: PredictionResponse;
  fairer_decision: Record<string, unknown>;
  bias_impact: Record<string, boolean>;
  llm_prompt: string;
};

type RequestOptions = RequestInit & {
  skipUserId?: boolean;
};

function isBrowser() {
  return typeof window !== "undefined";
}

function getClientUserId() {
  if (!isBrowser()) {
    return "anonymous";
  }

  const existing = window.localStorage.getItem(USER_ID_KEY);
  if (existing) {
    return existing;
  }

  const nextId = window.crypto?.randomUUID?.() || `fairlens-${Date.now()}`;
  window.localStorage.setItem(USER_ID_KEY, nextId);
  return nextId;
}

async function parseError(response: Response) {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    return JSON.stringify(body);
  } catch {
    return response.statusText || "Request failed";
  }
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!options.skipUserId) {
    headers.set("X-User-Id", getClientUserId());
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json() as Promise<T>;
}

export function saveLastAudit(audit: FairnessAudit) {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(LAST_AUDIT_KEY, JSON.stringify(audit));
}

export function readLastAudit(): FairnessAudit | null {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(LAST_AUDIT_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as FairnessAudit;
  } catch {
    window.localStorage.removeItem(LAST_AUDIT_KEY);
    return null;
  }
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function getApiHealth() {
  return apiRequest<{ status: string; trained: boolean; domain?: string; message: string }>(
    "/",
    { skipUserId: true },
  );
}

export async function uploadDataset(
  file: File,
  options: { targetCol: string; sensitiveCol: string; domain?: string },
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_col", options.targetCol);
  formData.append("sensitive_col", options.sensitiveCol);
  formData.append("domain", options.domain || "custom");

  const audit = await apiRequest<FairnessAudit>("/upload", {
    method: "POST",
    body: formData,
  });
  saveLastAudit(audit);
  return audit;
}

export function getCurrentAudit() {
  return apiRequest<FairnessAudit>("/audit");
}

export function getSchema() {
  return apiRequest<SchemaResponse>("/schema");
}

export function predictApplicant(payload: Record<string, unknown>) {
  return apiRequest<PredictionResponse>("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getStatus() {
  return apiRequest<StatusResponse>("/status");
}

export function getDashboardStats(sensitiveCols: string[], useDebiased: boolean = false) {
  return apiRequest<DashboardStats>("/dashboard-stats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sensitive_cols: sensitiveCols, use_debiased: useDebiased }),
  });
}

export function getLlmContext() {
  return apiRequest<{ audit_id?: string; context: string }>("/llm-context");
}

export function compareCandidates(payload: CompareRequest) {
  return apiRequest<CompareResponse>("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listAudits() {
  return apiRequest<AuditSummary[]>("/audits");
}

export function getSavedAudit(auditId: string) {
  return apiRequest<FairnessAudit>(`/audits/${auditId}`);
}

export function loadSavedAudit(auditId: string) {
  return apiRequest<{ status: string; audit_id: string; audit: FairnessAudit; schema: SchemaResponse }>(
    `/audits/${auditId}/load`,
    { method: "POST" },
  );
}

export function deleteSavedAudit(auditId: string) {
  return apiRequest<{ deleted: boolean; audit_id: string }>(`/audits/${auditId}`, {
    method: "DELETE",
  });
}

export function getReportExportUrl(auditId: string) {
  return `${API_BASE_URL}/export/report/${auditId}`;
}

export function getCsvExportUrl(auditId: string) {
  return `${API_BASE_URL}/export/csv/${auditId}`;
}

export async function remediateAndDownload(
  auditId: string,
  originalFile?: File | null
): Promise<{
  blob: Blob;
  filename: string;
  summary: {
    rows_changed: number;
    pct_changed: number;
    original_di_ratio: number;
    debiased_di_ratio: number;
  } | null;
}> {
  const requestOptions: RequestInit = {
    method: "POST",
    headers: { "X-User-Id": getClientUserId() },
    cache: "no-store",
  };

  if (originalFile) {
    const formData = new FormData();
    formData.append("file", originalFile);
    requestOptions.body = formData;
  }

  const response = await fetch(`${API_BASE_URL}/remediate/${auditId}`, requestOptions);

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] || "debiased_dataset.csv";
  
  const summaryRaw = response.headers.get("X-Remediation-Summary");
  const summary = summaryRaw ? JSON.parse(summaryRaw) : null;

  return { blob, filename, summary };
}
