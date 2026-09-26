// Backend /api/v1 javoblariga mos turlar.

export type Level = 'high' | 'medium' | 'low'
export type Role = 'admin' | 'analyst' | 'manager' | 'auditor'
export type ExpertStatus = 'pending' | 'confirmed' | 'rejected' | 'need_info' | 'sent_review'
export type DecisionType = 'confirmed' | 'rejected' | 'need_info' | 'sent_review'
export type AlertStatus = 'new' | 'in_review' | 'confirmed' | 'rejected' | 'closed'
export type RiskTypeCode = 'R01' | 'R02' | 'R03' | 'R04' | 'R05' | 'R06' | 'R07' | 'R08'

export interface Envelope<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string; details?: unknown } | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface User {
  id: number
  username: string
  full_name: string
  role: Role
  role_label: string
  region_id: string | null
  region_name: string | null
  organization: string
  permissions: string[]
}

export interface LoginResult {
  token: string
  expires_at: string
  user: User
}

export interface RegionRef {
  id: string
  name: string
  short_name: string
  geo_key: string
}

export interface RiskType {
  code: RiskTypeCode
  name: string
  icon: string
  description: string
}

export interface Meta {
  regions: RegionRef[]
  sectors: { id: string; name: string; icon: string }[]
  risk_types: RiskType[]
  relation_types: Record<string, string>
  levels: Record<Level, string>
  expert_statuses: Record<ExpertStatus, string>
  decision_types: Record<DecisionType, string>
  alert_statuses: Record<AlertStatus, string>
  size_groups: Record<string, string>
  roles: Record<Role, string>
  dq_dimensions: Record<string, string>
  dq_low_threshold: number
  thresholds: { low: number; high: number; is_mvp_default: boolean }
  active_model: { name: string; version: string; key: string } | null
  last_computed_at: string | null
  data_freshness_at: string | null
  period: { start: string; end: string; data_version: string } | null
  synthetic: boolean
}

export interface RegionStat {
  id: string
  name: string
  short_name: string
  geo_key: string
  restricted: boolean
  subjects: number | null
  high: number | null
  medium: number | null
  risk_index: number | null
  avg_dq: number | null
  new_alerts: number | null
  updated_at: string | null
}

export interface CaseRow {
  code: string
  region_id: string
  sector_id: string
  score: number
  level: Level
  confidence: Level
  dq_score: number
  primary_risk_type: RiskTypeCode
  expert_status: ExpertStatus
}

export interface ChainStep {
  key: string
  label: string
  value: number | string
  unit: string
}

export interface Dashboard {
  filter: { region: string | null; scoped: boolean }
  thresholds: { low: number; high: number }
  kpis: {
    analyzed: number
    high_priority: number
    medium_priority: number
    new_alerts: number
    new_alerts_7d: number
    avg_dq: number | null
    low_dq_subjects: number
    active_model: string | null
    last_update: string | null
  }
  regions: RegionStat[]
  sectors: { id: string; name: string; subjects: number; high: number; medium: number; share: number }[]
  risk_types: { code: RiskTypeCode; count: number }[]
  trend: { period: string; high_share: number; high_est: number; mean_score: number }[]
  distribution: { from: number; to: number; count: number }[]
  top_cases: CaseRow[]
  chain: ChainStep[]
}

export interface SubjectRow {
  code: string
  region_id: string
  sector_id: string
  size_group: string
  stir: string
  score: number
  level: Level
  confidence: Level
  confidence_value: number
  primary_risk_type: RiskTypeCode
  risk_types: RiskTypeCode[]
  dq_score: number
  expert_status: ExpertStatus
  computed_at: string
}

export interface Risk {
  score: number
  level: Level
  confidence: Level
  confidence_value: number
  dq_score: number
  dq_dimensions: Record<string, number>
  primary_risk_type: RiskTypeCode
  risk_types: RiskTypeCode[]
  components: Record<string, number>
  anomaly_score: number
  expert_status: ExpertStatus
  model_version: string
  data_version: string
  period_start: string
  period_end: string
  computed_at: string
  thresholds: { low: number; high: number }
}

export interface Factor {
  rank: number
  feature: string
  factor: string
  risk_type: RiskTypeCode
  current_value: number | null
  baseline_low: number | null
  baseline_high: number | null
  unit: string
  deviation: Level
  impact: number
  source: string
}

export interface SubjectDetail {
  code: string
  region: { id: string; name: string }
  sector: { id: string; name: string }
  size_group: string
  org_form: string
  stir: string
  stir_masked: boolean
  registered_at: string
  source_count: number
  history_months: number
  duplicate_records: number
  is_synthetic: boolean
  risk: Risk
  factors: Factor[]
  alert: { code: string; status: AlertStatus; severity: Level; detected_at: string; analyst_id: number | null } | null
}

export interface TimePoint {
  period: string
  value: number | null
  peer_median: number | null
  expected: number | null
  expected_low: number | null
  expected_high: number | null
  deviation_pct: number | null
  outside: boolean
  registry: number | null
}

export interface TimeSeries {
  metric: string
  label: string
  unit: string
  points: TimePoint[]
  peer_group: string
  source: string
}

export interface PeerGroup {
  group: 'sector' | 'region' | 'size'
  label: string
  n: number
  p10: number
  p25: number
  median: number
  p75: number
  p90: number
  percentile: number
}

export interface Peers {
  code: string
  metrics: { metric: string; label: string; unit: string; value: number | null; groups: PeerGroup[] }[]
}

export interface GraphNode {
  id: string
  region_id: string
  sector_id: string
  score: number | null
  level: Level | null
  depth: number
  is_center: boolean
  restricted: boolean
  hidden_neighbors: number
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  label: string
  weight: number
  structural: boolean
  risky_path: boolean
}

export interface Relations {
  center: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  summary: { direct: number; risky_direct: number; second_level_shown: number; hidden: number }
}

export interface Explanation {
  paragraphs: string[]
  basis_note: string
  disclaimer: string
  generator: string
  inputs: Record<string, unknown>
  source: 'ai' | 'template'
  model: string | null
  model_label: string | null
  validated: boolean
  fallback_reason: string | null
  fallback_code: string | null
  created_at: string | null
}

export interface AiStatus {
  enabled: boolean
  configured: boolean
  model: string
  model_label: string
  effort: string
  timeout_seconds: number
  prompt_version: string
  mode: 'ai' | 'template'
  session: {
    calls: number
    ok: number
    rejected: number
    errors: number
    last_ok_at: string | null
    last_error: string | null
    last_error_at: string | null
    avg_latency_ms: number | null
  }
  totals: { ok: number; rejected: number; error: number; input_tokens: number; output_tokens: number }
  recent: {
    subject_code: string
    status: 'ok' | 'rejected' | 'error'
    model: string
    reason: string | null
    input_tokens: number
    output_tokens: number
    latency_ms: number
    created_at: string
  }[]
}

export interface AiTestResult {
  ok: boolean
  message: string
  model?: string
  display_name?: string | null
  latency_ms?: number
}

export interface Decision {
  id: number
  decision: DecisionType
  comment: string
  user: { id: number; full_name: string; role: Role }
  created_at: string
  score_at_decision: number
  model_version: string
}

export interface AlertRow {
  id: number
  code: string
  subject_code: string
  sector_id: string
  region_id: string
  risk_type: RiskTypeCode
  severity: Level
  score: number
  status: AlertStatus
  detected_at: string
  updated_at: string
  analyst: { id: number; full_name: string } | null
}

export interface AlertPage extends Page<AlertRow> {
  counts: Partial<Record<AlertStatus, number>>
}

export interface DataSource {
  id: number
  code: string
  name: string
  type: string
  status: 'active' | 'delayed' | 'error' | 'disabled'
  description: string
  last_load_at: string | null
  rows: number
  rejected: number
  quality_score: number | null
  last_error: string | null
}

export interface ImportJob {
  id: number
  filename: string
  format: string
  stage: string
  status: string
  total_rows: number
  accepted: number
  rejected: number
  duplicates: number
  columns: string[]
  mapping: Record<string, string | null>
  dq: { score?: number; dimensions?: Record<string, number>; matched_subjects?: number; unknown_stir?: number }
  errors: { row: number; messages: string[] }[]
  data_source_id: number | null
  created_at: string
  finished_at: string | null
  target_fields: Record<string, { label: string; required: boolean }>
  preview?: Record<string, unknown>[]
}

export interface Job {
  id: number
  type: string
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  progress: number
  result: Record<string, unknown>
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface ModelRow {
  id: number
  key: string
  name: string
  version: string
  algorithm: string
  training_dataset: string
  features: string[]
  metrics: Record<string, number | string>
  threshold: Record<string, number>
  drift: { psi?: number; status?: string }
  status: 'DRAFT' | 'TESTING' | 'APPROVED' | 'ACTIVE' | 'ARCHIVED'
  created_by: string
  approved_by: string | null
  approved_at: string | null
  created_at: string
  implemented: boolean
  allowed_transitions: string[]
}

export interface MonitoringPoint {
  period: string
  mean_score: number
  high_share: number
  anomalies: number
  mean_confidence: number
  psi: number
  distribution: number[]
}

export interface Monitoring {
  model: ModelRow | null
  series: MonitoringPoint[]
  rejection: { month: string; rejected: number; total: number; rate: number | null }[]
  current: { psi: number | null; rejection_rate: number | null; mean_confidence: number | null; anomalies: number | null }
  limits: { psi: number; rejection_rate: number; confidence_drop: number }
  warnings: { code: string; message: string }[]
  status: 'normal' | 'review_required'
  status_message: string
}

export interface AuditRow {
  id: number
  at: string
  username: string
  action: string
  object_type: string
  object_id: string | null
  old_value: unknown
  new_value: unknown
  ip: string | null
  session_id: string | null
}

export interface AuditPage extends Page<AuditRow> {
  actions: string[]
  users: string[]
}

export interface ReportMeta {
  number: string
  type: string
  type_label: string
  title: string
  created_at: string
  period_start: string
  period_end: string
  model_version: string
  data_version: string
  created_by: string
  synthetic: boolean
  disclaimer: string
}

export interface SubjectReportContent {
  kind: 'subject'
  subject: Pick<SubjectDetail, 'code' | 'region' | 'sector' | 'size_group' | 'stir' | 'registered_at' | 'source_count' | 'history_months'>
  risk: Risk
  factors: Factor[]
  explanation: Explanation
  decisions: Decision[]
  relations: Relations['summary']
}

export interface AggregateReportContent {
  kind: 'aggregate'
  summary: { subjects: number; high: number; medium: number; avg_dq: number | null; low_dq: number; thresholds: { low: number; high: number } }
  by_region: { id: string; name: string; subjects: number; high: number; medium: number }[]
  by_sector: { id: string; name: string; subjects: number; high: number; medium: number }[]
  by_risk_type: { code: string; name: string; count: number }[]
  top: { code: string; region: string; sector: string; score: number; level: string; confidence: string; risk_type: string; dq_score: number; expert_status: string }[]
}

export interface ReportResult {
  id: number
  meta: ReportMeta
  content: SubjectReportContent | AggregateReportContent
}

export interface ReportListItem extends ReportMeta {
  id: number
}

export interface SettingsAll {
  risk_thresholds: { low: number; high: number; updated_at: string | null; updated_by: string | null; note: string }
  drift_thresholds: { psi: number; rejection_rate: number; confidence_drop: number } | null
  retention_policy: { data_type: string; retention: string; archive: string; deletion: string }[]
  can_edit: boolean
}

export interface UserRow {
  id: number
  username: string
  full_name: string
  role: Role
  role_label: string
  region_id: string | null
  region_name: string | null
  is_active: boolean
  last_login_at: string | null
}

export interface Calibration {
  note: string
  sources: { what: string; as_of: string; publisher: string; url: string }[]
  assumptions: string[]
  check: {
    sectors: {
      id: string
      name: string
      official_share: number
      sample_share: number
      official_mean_monthly_mln: number
      sample_mean_monthly_mln: number
      sample_median_monthly_mln: number
    }[]
    regions: { id: string; name: string; official_share: number; sample_share: number }[]
    size_groups: Record<string, number>
  }
}
