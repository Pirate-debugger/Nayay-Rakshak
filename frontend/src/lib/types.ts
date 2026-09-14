export type VerificationStatus =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONFLICTING'
  | 'UNVERIFIED';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'SEVERE';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface DocumentMeta {
  id: number;
  user_id: number;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  status?: 'QUARANTINED' | 'SCANNING' | 'EXTRACTING' | 'INDEXING' | 'READY' | 'FAILED' | string;
  error_message?: string;
  pii_redacted: boolean;
  created_at: string;
}

export interface DocumentDetail extends DocumentMeta {
  chunk_count: number;
  preview_text: string;
}

export interface ClauseItem {
  clause_id: string;
  category: string;
  title: string;
  original_text: string;
  plain_english: string;
  plain_hindi: string;
  risk_level: RiskLevel;
  page_number: number;
  recommendations?: string;
}

export interface RiskItem {
  risk_id: string;
  severity: RiskLevel;
  category: string;
  title: string;
  description: string;
  clause_reference: string;
  countermeasure: string;
}

export interface ObligationItem {
  obligation_id: string;
  responsible_party: string;
  action: string;
  deadline_or_frequency: string;
  penalty_for_breach: string;
}

export interface MissingClauseItem {
  clause_name: string;
  importance: 'CRITICAL' | 'RECOMMENDED' | 'STANDARD';
  why_needed: string;
  suggested_language: string;
  risk_if_missing: string;
}

export interface AnalysisResponse {
  document_id: number;
  summary_citizen: string;
  summary_legal: string;
  summary_hindi: string;
  flesch_kincaid_score: number;
  reading_level: string;
  clauses: ClauseItem[];
  risks: RiskItem[];
  obligations: ObligationItem[];
  missing_clauses: MissingClauseItem[];
}

export interface ClauseDiffItem {
  category: string;
  change_type: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'UNCHANGED';
  base_text?: string;
  target_text?: string;
  risk_delta: 'INCREASED_RISK' | 'DECREASED_RISK' | 'NEUTRAL';
  impact_analysis: string;
}

export interface RiskDeltaSummary {
  base_high_risks: number;
  target_high_risks: number;
  net_risk_verdict: string;
  critical_warnings: string[];
}

// ── Semantic Comparison Types ────────────────────────────────────────────────

export type ComparisonCategory =
  | 'IDENTICAL'
  | 'SIMILAR'
  | 'MODIFIED'
  | 'NEW'
  | 'REMOVED'
  | 'CONFLICTING'
  | 'MISSING';

export type DifferenceDimension =
  | 'STRUCTURAL'
  | 'OBLIGATION'
  | 'RIGHTS'
  | 'FINANCIAL'
  | 'DEADLINE'
  | 'LIABILITY'
  | 'TERMINATION'
  | 'JURISDICTION'
  | 'GENERAL_TERMS';

export type MaterialityLevel =
  | 'CRITICAL'
  | 'MATERIAL'
  | 'MEDIUM'
  | 'MINOR'
  | 'NEGLIGIBLE';

export interface DocumentEvidence {
  document_id: number;
  document_title: string;
  clause_id?: string;
  section_heading: string;
  page_number: number;
  verbatim_quote: string;
  char_start?: number;
  char_end?: number;
}

export interface ComparisonFindingItem {
  finding_id: string;
  category: ComparisonCategory;
  dimension: DifferenceDimension;
  title: string;
  document_a_evidence?: DocumentEvidence;
  document_b_evidence?: DocumentEvidence;
  difference_explanation: string;
  materiality: MaterialityLevel;
  risk_implications: string;
  confidence: number;
  semantic_similarity: number;
}

export interface StructuralDiff {
  doc_a_clause_count: number;
  doc_b_clause_count: number;
  aligned_clause_count: number;
  reordered_clause_count: number;
  missing_in_b_count: number;
  new_in_b_count: number;
  structural_alignment_score: number;
}

export interface ComparisonResponse {
  base_document_id: number;
  target_document_id: number;
  base_title: string;
  target_title: string;
  overall_verdict: string;
  summary: RiskDeltaSummary;
  clause_diffs: ClauseDiffItem[];
  structural_diff?: StructuralDiff;
  findings: ComparisonFindingItem[];
  dimensions_analyzed: string[];
}

export interface CitationItem {
  page_number: number;
  section_title: string;
  verbatim_quote: string;
  relevance_score: number;
}

export interface QAEvidenceItem {
  evidence_id: string;
  verbatim_quote: string;
  source_title: string;
  authority_tier: string;
  section_or_page?: string;
  provenance_url?: string;
}

export interface StructuredAnswerSections {
  plain_language_answer: string;
  what_document_says?: string;
  applicable_legal_source?: string;
  evidence: QAEvidenceItem[];
  important_uncertainty?: string;
  potential_next_steps: string[];
  questions_for_professional: string[];
  legal_disclaimer: string;
}

export interface QAContextMetadata {
  jurisdiction: string;
  document_context: string;
  relevant_dates: string[];
  legal_domain: string;
  missing_facts: string[];
}

export interface QAResponse {
  question: string;
  answer: string;
  confidence_score: number;
  citations: CitationItem[];
  is_found_in_document: boolean;
  requirement_type?: string;
  context_metadata?: QAContextMetadata;
  structured_sections?: StructuredAnswerSections;
  language?: string;
  disclaimer?: string;
}

export interface ClaimVerificationItem {
  claim_id: string;
  claim_text: string;
  evidence_source: string;
  page_or_section?: string;
  source_authority: string;
  source_date_or_version?: string;
  verification_status: VerificationStatus;
  confidence_strength: number;
  evidence_snippet?: string;
  reasoning: string;
}

export interface VerificationBatchResponse {
  document_id?: number;
  total_claims: number;
  results: ClaimVerificationItem[];
  summary_verdict: string;
}

export interface BriefResponse {
  id: number;
  document_id: number;
  title: string;
  client_name: string;
  brief_markdown: string;
  key_issues: string[];
  questions_for_lawyer: string[];
  created_at: string;
}

export interface LegalAidResource {
  id: string;
  name: string;
  organization_type: string;
  jurisdiction: string;
  phone_or_helpline: string;
  portal_url: string;
  description: string;
  services_offered: string[];
  physical_address?: string;
}

export interface EligibilityCheckResponse {
  is_eligible_for_free_legal_aid: boolean;
  governing_statute: string;
  statutory_clause: string;
  eligibility_reasons: string[];
  annual_income_limit_for_state: number;
  recommended_authorities: LegalAidResource[];
  action_checklist: string[];
}

export interface GlossaryEntry {
  term: string;
  hindi_term: string;
  transliteration: string;
  plain_english: string;
  plain_hindi: string;
  category: string;
  example: string;
}

export interface DeterministicCurrency {
  amount: number;
  raw_symbol?: string;
  currency_code: string;
  unit_multiplier: number;
  standardized_inr_equivalent?: number;
  raw_match: string;
}

export interface DeterministicPercentage {
  value_percent: number;
  is_per_annum: boolean;
  raw_match: string;
}

export interface DeterministicDuration {
  duration_value: number;
  unit: string;
  duration_days: number;
  raw_match: string;
}

export interface DeterministicDate {
  date_iso: string;
  raw_match: string;
  is_relative: boolean;
}

export interface DeterministicSection {
  section_number: string;
  prefix: string;
  raw_match: string;
}

export interface DeterministicFacts {
  currencies: DeterministicCurrency[];
  percentages: DeterministicPercentage[];
  durations: DeterministicDuration[];
  dates: DeterministicDate[];
  sections: DeterministicSection[];
}

export interface ClauseSemanticInterpretation {
  parties_affected: string[];
  obligations: string[];
  rights: string[];
  prohibitions: string[];
  conditions: string[];
  triggers: string[];
  deadlines: string[];
  monetary_values: string[];
  penalties: string[];
  termination_conditions: string[];
  jurisdiction?: string;
  governing_law?: string;
  arbitration?: string;
  confidentiality?: string;
  indemnity?: string;
  liability?: string;
  intellectual_property?: string;
  renewal?: string;
  dispute_resolution?: string;
  privacy_data_terms?: string;
}

export interface EvidenceLocation {
  page_number: number;
  section_heading?: string;
  byte_start?: number;
  byte_end?: number;
  verbatim_quote: string;
}

export interface StructuredClauseRecord {
  clause_id: string;
  section?: string;
  title: string;
  page: number;
  clause_type: string;
  original_text: string;
  simplified_explanation: string;
  plain_hindi?: string;
  evidence_location: EvidenceLocation;
  extraction_confidence: number;
  interpretation_confidence: number;
  deterministic_facts: DeterministicFacts;
  structured_interpretation: ClauseSemanticInterpretation;
  statutory_conflict_flag: boolean;
  potential_violates_statute?: string;
  recommendations: string[];
}


// --- Action Navigator Types ---

export type UrgencyLevel =
  | 'IMMEDIATE'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFORMATIONAL';

export type IssueSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type EscalationTriggerType =
  | 'HIGH_FINANCIAL_EXPOSURE'
  | 'SIGNIFICANT_DEADLINE'
  | 'COURT_MATTER'
  | 'CRIMINAL_MATTER'
  | 'SERIOUS_RIGHTS_IMPACT'
  | 'CONFLICTING_AUTHORITIES'
  | 'INSUFFICIENT_EVIDENCE'
  | 'CRITICAL_RISK_DETECTED'
  | 'UNCAPPED_INDEMNITY'
  | 'MISSING_DISPUTE_RESOLUTION'
  | 'MULTIPLE_HIGH_RISKS'
  | 'JURISDICTION_CONFLICT';

export interface NavFactItem {
  fact: string;
  source: string;
  confidence: number;
  category: string;
}

export interface NavDocumentItem {
  document_name: string;
  why_needed: string;
  urgency: UrgencyLevel;
  consequence_if_missing: string;
  source?: string;
}

export interface NavDateItem {
  date_description: string;
  estimated_date?: string;
  consequence: string;
  urgency: UrgencyLevel;
  source: string;
}

export interface NavIssueItem {
  issue: string;
  explanation: string;
  potential_impact: string;
  severity: IssueSeverity;
  category: string;
  source_risk_id?: string;
}

export interface NavQuestionItem {
  question: string;
  purpose: string;
  ask_whom: string;
  priority: UrgencyLevel;
  source_risk_id?: string;
}

export interface NavActionStep {
  step_number: number;
  action: string;
  reason: string;
  evidence_source: string;
  urgency: UrgencyLevel;
  dependency?: string;
  is_professional_review_step: boolean;
}

export interface NavEscalationTrigger {
  trigger_type: EscalationTriggerType;
  reason: string;
  severity: IssueSeverity;
  recommended_resource: string;
  source_risk_id?: string;
}

export interface ActionNavigatorResponse {
  document_id: number;
  document_title: string;
  engine_version: string;
  known_facts: NavFactItem[];
  unknown_facts: NavFactItem[];
  important_documents: NavDocumentItem[];
  important_dates: NavDateItem[];
  potential_issues: NavIssueItem[];
  questions_to_ask: NavQuestionItem[];
  possible_next_steps: NavActionStep[];
  when_to_seek_professional_help: NavEscalationTrigger[];
  professional_review_recommended: boolean;
  professional_review_urgency: UrgencyLevel;
  disclaimer: string;
  generated_at: string;
}

// ── Additional Strongly Typed Models ───────────────────────────────────────

export interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  importance: 'CRITICAL' | 'HIGH' | 'STANDARD' | string;
}

export interface DocumentChecklistResponse {
  title: string;
  jurisdiction: string;
  items: ChecklistItem[];
}

export type FindingType =
  | 'DETERMINISTIC_RULE'
  | 'AI_ASSISTED_PATTERN'
  | 'CROSS_CLAUSE_CONFLICT'
  | 'MISSING_STATUTORY_PROTECTION';

export interface RiskEvidenceLocation {
  page_number: number;
  section_heading?: string;
  verbatim_quote: string;
  char_start?: number;
  char_end?: number;
}

export interface RiskRecord {
  risk_id: string;
  category: string;
  severity: RiskLevel | 'CRITICAL';
  title: string;
  finding: string;
  plain_language_explanation: string;
  why_it_matters: string;
  evidence: RiskEvidenceLocation;
  affected_party: string;
  confidence: number;
  recommended_question: string;
  professional_review_recommended: boolean;
  rule_id?: string;
  rule_version?: string;
  finding_type: FindingType;
  statutory_cross_reference?: string;
  is_camouflaged: boolean;
}

export interface RiskSummaryStats {
  total_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  overall_health_verdict: string;
}

export interface RiskRuleInfo {
  rule_id: string;
  version: string;
  category: string;
  default_severity: string;
  title: string;
  description: string;
  statutory_reference?: string;
}

export interface RiskEngineResult {
  document_id?: number;
  engine_version: string;
  ruleset_version: string;
  summary: RiskSummaryStats;
  risks: RiskRecord[];
  missing_protections: RiskRecord[];
  audit_trail: Array<Record<string, unknown>>;
}

export interface RetrievalFilter {
  jurisdiction?: string;
  allow_cross_jurisdiction?: boolean;
  court?: string;
  legal_domain?: string;
  as_of_date?: string;
  min_authority_tier?: string;
  allowed_statuses?: string[];
}

export interface RetrievalCitationRecord {
  source_id: string;
  title: string;
  authority: string;
  authority_tier: string;
  evidence_type: string;
  section_or_page: string;
  publication_date?: string;
  effective_date?: string;
  retrieval_timestamp: string;
  url_or_reference: string;
  supporting_text: string;
  relevance_score: number;
  provenance?: Record<string, unknown>;
}

export interface RetrievalResultItem {
  item_id: string;
  evidence_type: string;
  tier: string;
  title: string;
  content: string;
  citation: RetrievalCitationRecord;
  keyword_score: number;
  semantic_score: number;
  tier_boost: number;
  final_score: number;
  jurisdiction: string;
  effective_from?: string;
  effective_to?: string;
  status: string;
}

export interface RetrievalSearchResponse {
  query: string;
  classified_intent: string;
  applied_filters: RetrievalFilter;
  total_found: number;
  has_authoritative_evidence: boolean;
  explicit_unretrieved_disclaimer?: string;
  user_document_items: RetrievalResultItem[];
  legal_authority_items: RetrievalResultItem[];
  secondary_items: RetrievalResultItem[];
  reranked_items: RetrievalResultItem[];
  evaluation_metrics?: Record<string, number>;
}

export interface AuthoritativeSourceRecord {
  source_id: string;
  title: string;
  statute: string;
  section: string;
  domain: string;
  jurisdiction: string;
  status: string;
  authority_tier: string;
  description: string;
  official_reference_url?: string;
}

export interface ClaimVerificationDetail {
  claim_id: string;
  claim_text: string;
  verification_status: VerificationStatus;
  confidence_score: number;
  supporting_evidence: Array<{
    source_title: string;
    authority_tier: string;
    verbatim_quote: string;
    section_or_page?: string;
    relevance: number;
  }>;
  contradicting_evidence: Array<{
    source_title: string;
    authority_tier: string;
    verbatim_quote: string;
    section_or_page?: string;
  }>;
  reasoning: string;
  action_recommended?: string;
}

export interface VerificationMetrics {
  total_claims: number;
  supported_claims: number;
  partially_supported_claims: number;
  unsupported_claims: number;
  conflicting_claims: number;
  unverified_claims: number;
  overall_grounding_score: number;
}

export interface ClaimVerificationPipelineResponse {
  user_question: string;
  draft_answer: string;
  final_response: string;
  safety_gate_action: string;
  claims: ClaimVerificationDetail[];
  metrics: VerificationMetrics;
  citations_verified: string[];
  citations_rejected: string[];
  never_hallucination_free_compliance: boolean;
}
