// Domen servislari: UI faqat shu funksiyalar orqali backend bilan ishlaydi.
import { api, download } from './http'
import type {
  AiStatus,
  AiTestResult,
  AlertPage,
  AlertRow,
  AlertStatus,
  AuditPage,
  Calibration,
  Dashboard,
  DataSource,
  Decision,
  DecisionType,
  Explanation,
  ImportJob,
  Job,
  LoginResult,
  Meta,
  ModelRow,
  Monitoring,
  Page,
  Peers,
  Relations,
  ReportListItem,
  ReportResult,
  SettingsAll,
  SubjectDetail,
  SubjectRow,
  TimeSeries,
  User,
  UserRow,
} from '@/types/api'

export interface SubjectQuery {
  region?: string
  sector?: string
  level?: string
  risk_type?: string
  expert_status?: string
  dq?: string
  confidence?: string
  q?: string
  sort?: string
  order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

function clean<T extends object>(q: T): Partial<T> {
  return Object.fromEntries(Object.entries(q).filter(([, v]) => v !== '' && v !== null && v !== undefined)) as Partial<T>
}

export const authApi = {
  login: (username: string, password: string) => api.post<LoginResult>('/auth/login', { username, password }),
  me: () => api.get<User>('/auth/me'),
  logout: () => api.post<{ logged_out: boolean }>('/auth/logout'),
}

export const metaApi = {
  get: () => api.get<Meta>('/meta'),
}

export const dashboardApi = {
  get: (region?: string | null) => api.get<Dashboard>('/dashboard', clean({ region })),
}

export const subjectsApi = {
  list: (q: SubjectQuery) => api.get<Page<SubjectRow>>('/subjects', clean(q)),
  exportCsv: (q: SubjectQuery) => download('/subjects/export.csv', clean({ ...q, page: undefined }), 'rasad_subyektlar.csv'),
  get: (code: string) => api.get<SubjectDetail>(`/subjects/${code}`),
  timeseries: (code: string, metric = 'turnover') => api.get<TimeSeries>(`/subjects/${code}/timeseries`, { metric }),
  peers: (code: string) => api.get<Peers>(`/subjects/${code}/peers`),
  relations: (code: string, depth = 2, maxNodes = 40) =>
    api.get<Relations>(`/subjects/${code}/relations`, { depth, max_nodes: maxNodes }),
  explanation: (code: string) => api.get<Explanation>(`/subjects/${code}/explanation`),
  regenerateExplanation: (code: string) => api.post<Explanation>(`/subjects/${code}/explanation/regenerate`),
  decisions: (code: string) => api.get<Decision[]>(`/subjects/${code}/decisions`),
}

export const decisionsApi = {
  create: (subject_code: string, decision: DecisionType, comment: string) =>
    api.post<Decision>('/expert-decisions', { subject_code, decision, comment }),
}

export const alertsApi = {
  list: (q: Record<string, unknown>) => api.get<AlertPage>('/alerts', clean(q)),
  analysts: () => api.get<{ id: number; full_name: string; region_id: string | null }[]>('/alerts/analysts'),
  update: (ids: number[], patch: { status?: AlertStatus; analyst_id?: number; unassign?: boolean }) =>
    api.patch<{ updated: number; items: AlertRow[] }>('/alerts', { ids, ...patch }),
}

export const reportsApi = {
  create: (report_type: string, params: Record<string, string>) =>
    api.post<ReportResult>('/reports', { report_type, params }),
  list: () => api.get<ReportListItem[]>('/reports'),
  get: (id: number) => api.get<ReportResult>(`/reports/${id}`),
  download: (id: number, format: 'pdf' | 'xlsx' | 'csv') =>
    download(`/reports/${id}/download`, { format }, `rasad_hisobot.${format}`),
}

export const dataApi = {
  sources: () => api.get<DataSource[]>('/data-sources'),
  calibration: () => api.get<Calibration>('/data-sources/calibration'),
  lineage: (id: number) => api.get<Record<string, string>[]>(`/data-sources/${id}/lineage`),
  imports: () => api.get<ImportJob[]>('/imports'),
  upload: (file: File, dataSourceId?: number | null) => {
    const form = new FormData()
    form.append('file', file)
    if (dataSourceId) form.append('data_source_id', String(dataSourceId))
    return api.upload<ImportJob>('/imports', form)
  },
  getImport: (id: number) => api.get<ImportJob>(`/imports/${id}`),
  setMapping: (id: number, mapping: Record<string, string | null>) =>
    api.post<ImportJob>(`/imports/${id}/mapping`, { mapping }),
  validate: (id: number) => api.post<ImportJob>(`/imports/${id}/validate`),
  confirm: (id: number) => api.post<{ job: Job; import: ImportJob }>(`/imports/${id}/confirm`),
  job: (id: number) => api.get<Job>(`/jobs/${id}`),
  jobs: () => api.get<Job[]>('/jobs'),
  recompute: () => api.post<Job>('/jobs/recompute'),
}

export const modelsApi = {
  list: () => api.get<ModelRow[]>('/models'),
  setStatus: (id: number, status: string) => api.post<ModelRow>(`/models/${id}/status`, { status }),
  monitoring: () => api.get<Monitoring>('/monitoring'),
}

export const auditApi = {
  list: (q: Record<string, unknown>) => api.get<AuditPage>('/audit', clean(q)),
}

export const settingsApi = {
  get: () => api.get<SettingsAll>('/settings'),
  setThresholds: (low: number, high: number) => api.put<{ low: number; high: number }>('/settings/thresholds', { low, high }),
}

export const usersApi = {
  list: () => api.get<UserRow[]>('/users'),
  update: (id: number, patch: Partial<Pick<UserRow, 'role' | 'region_id' | 'is_active'>>) =>
    api.patch<UserRow>(`/users/${id}`, patch),
}

export const aiApi = {
  status: () => api.get<AiStatus>('/ai/status'),
  test: () => api.post<AiTestResult>('/ai/test'),
}
