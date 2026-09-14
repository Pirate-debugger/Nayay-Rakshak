import {
  ActionNavigatorResponse,
  AnalysisResponse,
  AuthoritativeSourceRecord,
  BriefResponse,
  ChecklistItem,
  ClaimVerificationPipelineResponse,
  ComparisonResponse,
  DocumentChecklistResponse,
  DocumentDetail,
  DocumentMeta,
  EligibilityCheckResponse,
  GlossaryEntry,
  LegalAidResource,
  QAResponse,
  RetrievalFilter,
  RetrievalSearchResponse,
  RiskEngineResult,
  RiskRuleInfo,
  StructuredClauseRecord,
  User,
  VerificationBatchResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

let inMemoryToken: string | null = null;

export function getAuthToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== 'undefined') {
    return sessionStorage.getItem('nyaya_auth_token');
  }
  return null;
}

export function setAuthToken(token: string) {
  inMemoryToken = token;
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('nyaya_auth_token', token);
  }
}

export function clearAuthToken() {
  inMemoryToken = null;
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem('nyaya_auth_token');
  }
}

export async function initAuth(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        setAuthToken(data.access_token);
        return data.access_token;
      }
    }
  } catch {
    // No active session or refresh failed
  }
  return getAuthToken();
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers,
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errorDetail = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return (await res.json()) as T;
}

// Auth API
export async function registerUser(email: string, password: string, fullName: string) {
  const res = await request<{ access_token: string; user: User }>('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  setAuthToken(res.access_token);
  return res;
}

export async function loginUser(email: string, password: string) {
  const res = await request<{ access_token: string; user: User }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(res.access_token);
  return res;
}

export async function getCurrentUser(): Promise<User> {
  return request<User>('/auth/me');
}

// Documents API
export async function listDocuments(): Promise<DocumentMeta[]> {
  return request<DocumentMeta[]>('/documents/');
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`);
}

export async function uploadDocument(file: File, title?: string, redactPii = true): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  formData.append('redact_pii', String(redactPii));

  const token = getAuthToken();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

export async function loadSampleDocument(sampleKey: string): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append('sample_key', sampleKey);

  const token = getAuthToken();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE}/documents/load-sample`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load sample');
  }

  return res.json();
}

export async function deleteDocument(id: number): Promise<void> {
  await request<void>(`/documents/${id}`, { method: 'DELETE' });
}

// Analysis API
export async function analyzeDocument(documentId: number): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/analysis/${documentId}`, { method: 'POST' });
}

export async function getDocumentAnalysis(documentId: number): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/analysis/${documentId}`);
}

export async function getDocumentChecklist(documentId: number): Promise<DocumentChecklistResponse> {
  return request<DocumentChecklistResponse>(`/analysis/${documentId}/checklist`);
}

export async function getStructuredClauses(documentId: number): Promise<{ document_id: number; clause_count: number; clauses: StructuredClauseRecord[] }> {
  return request<{ document_id: number; clause_count: number; clauses: StructuredClauseRecord[] }>(
    `/analysis/${documentId}/clauses-structured`
  );
}

export async function extractSingleClause(
  clauseText: string,
  sectionTitle?: string,
  documentCategory?: string
): Promise<StructuredClauseRecord> {
  return request<StructuredClauseRecord>('/analysis/clause/extract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      clause_text: clauseText,
      section_title: sectionTitle,
      document_category: documentCategory,
    }),
  });
}

// Comparison API
export async function compareDocuments(baseId: number, targetId: number): Promise<ComparisonResponse> {
  return request<ComparisonResponse>('/comparison/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_document_id: baseId, target_document_id: targetId }),
  });
}

// Grounded Q&A API
export async function askQuestion(
  firstArg: number | string | undefined,
  secondArg?: string | number,
  language: string = 'en',
  jurisdiction?: string
): Promise<QAResponse> {
  let docId: number | undefined;
  let question: string = '';

  if (typeof firstArg === 'number') {
    docId = firstArg;
    question = typeof secondArg === 'string' ? secondArg : '';
  } else if (typeof firstArg === 'string') {
    question = firstArg;
    docId = typeof secondArg === 'number' ? secondArg : undefined;
  }

  return request<QAResponse>('/qa/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document_id: docId,
      language,
      jurisdiction,
    }),
  });
}

// Verification API
export async function verifyClaims(claims: string[], documentId?: number): Promise<VerificationBatchResponse> {
  return request<VerificationBatchResponse>('/verification/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, claims }),
  });
}

// Consultation Briefs API
export async function createBrief(documentId: number, clientName: string, specificQuestions?: string[]): Promise<BriefResponse> {
  return request<BriefResponse>('/briefs/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, client_name: clientName, specific_questions: specificQuestions }),
  });
}

export async function getBrief(briefId: number): Promise<BriefResponse> {
  return request<BriefResponse>(`/briefs/${briefId}`);
}

export function getExportBriefUrl(briefId: number): string {
  return `${API_BASE}/briefs/${briefId}/export`;
}

// Legal Aid API
export async function getLegalAidResources(query?: string, organizationType?: string): Promise<LegalAidResource[]> {
  const params = new URLSearchParams();
  if (query) params.append('query', query);
  if (organizationType) params.append('organization_type', organizationType);
  return request<LegalAidResource[]>(`/legal-aid/resources?${params.toString()}`);
}

export async function checkLegalAidEligibility(data: {
  annual_income: number;
  state: string;
  is_woman_or_child?: boolean;
  is_sc_or_st?: boolean;
  is_disabled?: boolean;
  is_trafficking_victim?: boolean;
  is_in_custody?: boolean;
  is_industrial_workman?: boolean;
}): Promise<EligibilityCheckResponse> {
  return request<EligibilityCheckResponse>('/legal-aid/check-eligibility', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// Glossary API
export async function getGlossary(query?: string): Promise<GlossaryEntry[]> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  return request<GlossaryEntry[]>(`/glossary/${params}`);
}

// NYAYA RAKSHAK - Advanced Subsystems API

// 1. Risk Engine API
export async function evaluateDocumentRisks(documentId: number): Promise<RiskEngineResult> {
  return request<RiskEngineResult>(`/analysis/${documentId}/risk-engine`, {
    method: 'POST',
  });
}

export async function evaluateTextRisks(text: string): Promise<RiskEngineResult> {
  return request<RiskEngineResult>('/analysis/risk-engine/evaluate-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

export async function getRiskRules(): Promise<RiskRuleInfo[]> {
  return request<RiskRuleInfo[]>('/analysis/risk-engine/rules');
}

// 2. Evidence-First Legal Retrieval API
export async function searchLegalEvidence(data: {
  query: string;
  document_chunks?: Array<Record<string, unknown>>;
  custom_filters?: RetrievalFilter;
  top_k?: number;
}): Promise<RetrievalSearchResponse> {
  return request<RetrievalSearchResponse>('/retrieval/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function evaluateRetrievalQuality(): Promise<Record<string, number>> {
  return request<Record<string, number>>('/retrieval/evaluate', {
    method: 'POST',
  });
}

export async function getAuthoritativeSources(domain?: string, jurisdiction?: string): Promise<AuthoritativeSourceRecord[]> {
  const params = new URLSearchParams();
  if (domain) params.append('domain', domain);
  if (jurisdiction) params.append('jurisdiction', jurisdiction);
  return request<AuthoritativeSourceRecord[]>(`/retrieval/sources?${params.toString()}`);
}

// 3. Claim Verification Pipeline API
export async function verifyClaimsPipeline(data: {
  user_question: string;
  draft_answer?: string;
  document_chunks?: Array<Record<string, unknown>>;
  jurisdiction?: string;
  as_of_date?: string;
}): Promise<ClaimVerificationPipelineResponse> {
  return request<ClaimVerificationPipelineResponse>('/verification/pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// Action Navigator API
export async function generateActionPlan(
  documentId: number
): Promise<ActionNavigatorResponse> {
  return request<ActionNavigatorResponse>(`/analysis/${documentId}/action-navigator`, {
    method: 'POST',
  });
}
