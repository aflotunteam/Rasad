import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import type { Envelope } from '@/types/api'

export const TOKEN_KEY = 'rasad.token'

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

// Xato kodlari uchun foydalanuvchiga tushunarli xabarlar (server xabari bo'lmasa).
const FALLBACK: Record<string, string> = {
  AUTH_001: 'Login yoki parol noto‘g‘ri',
  AUTH_002: 'Ruxsat mavjud emas',
  AUTH_003: 'Sessiya muddati tugagan. Qaytadan kiring',
  DATA_001: 'Ma’lumot topilmadi',
  DATA_002: 'Kiritilgan ma’lumotlar noto‘g‘ri',
  DATA_003: 'Subyekt topilmadi',
  MODEL_001: 'Model qoidasi buzildi',
  RISK_001: 'Xavf bahosi mavjud emas',
  IMPORT_001: 'Import xatosi',
  REPORT_001: 'Hisobot yaratib bo‘lmadi',
  SYSTEM_001: 'Server xatosi. Birozdan so‘ng qayta urinib ko‘ring',
  NETWORK: 'Server bilan aloqa yo‘q',
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* brauzer xotirasi mavjud bo'lmasa, sessiya faqat xotirada saqlanadi */
  }
}

export const http = axios.create({ baseURL: '/api/v1', timeout: 30000 })

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

function toApiError(err: unknown): ApiError {
  const ax = err as AxiosError<Envelope<unknown>>
  if (ax.response) {
    const body = ax.response.data
    const code = body?.error?.code ?? 'SYSTEM_001'
    const message = body?.error?.message ?? FALLBACK[code] ?? FALLBACK.SYSTEM_001
    return new ApiError(code, message, ax.response.status, body?.error?.details)
  }
  return new ApiError('NETWORK', FALLBACK.NETWORK, 0)
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const res = await http.request<Envelope<T>>(config)
    if (!res.data.success) {
      const e = res.data.error
      throw new ApiError(e?.code ?? 'SYSTEM_001', e?.message ?? FALLBACK.SYSTEM_001, res.status)
    }
    return res.data.data as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    const apiErr = toApiError(err)
    if (apiErr.status === 401 && onUnauthorized && !String(config.url).includes('/auth/login')) onUnauthorized()
    throw apiErr
  }
}

export const api = {
  get: <T>(url: string, params?: object) => request<T>({ method: 'GET', url, params }),
  post: <T>(url: string, data?: unknown) => request<T>({ method: 'POST', url, data }),
  put: <T>(url: string, data?: unknown) => request<T>({ method: 'PUT', url, data }),
  patch: <T>(url: string, data?: unknown) => request<T>({ method: 'PATCH', url, data }),
  upload: <T>(url: string, form: FormData) =>
    request<T>({ method: 'POST', url, data: form, headers: { 'Content-Type': 'multipart/form-data' } }),
}

/** Faylni yuklab olish: token sarlavhada yuboriladi, havolada ko'rinmaydi. */
export async function download(url: string, params?: object, fallbackName = 'rasad_fayl'): Promise<void> {
  try {
    const res = await http.get(url, { params, responseType: 'blob' })
    const disposition = String(res.headers['content-disposition'] ?? '')
    const match = /filename="?([^"]+)"?/.exec(disposition)
    const name = match?.[1] ?? fallbackName
    const href = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = href
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(href), 2000)
  } catch (err) {
    throw toApiError(err)
  }
}
