import type { AlertStatus, DecisionType, ExpertStatus, Level } from '@/types/api'

export const LEVEL_LABEL: Record<Level, string> = { high: 'Yuqori', medium: 'O‘rta', low: 'Past' }

export const LEVEL_COLOR: Record<Level, string> = {
  high: 'var(--risk-high)',
  medium: 'var(--risk-medium)',
  low: 'var(--risk-low)',
}

// ECharts CSS o'zgaruvchilarini o'qiy olmaydi, shuning uchun hex qiymatlar alohida.
export const HEX = {
  navy: '#0B1F3A',
  blue: '#216DF3',
  cyan: '#38BDF8',
  muted: '#607087',
  border: '#DDE7F0',
  grid: '#EDF2F8',
  high: '#D9534F',
  medium: '#D99B22',
  low: '#2FA36B',
  info: '#2878FF',
  surface: '#FFFFFF',
}

export const LEVEL_HEX: Record<Level, string> = { high: HEX.high, medium: HEX.medium, low: HEX.low }

export const CONFIDENCE_LABEL: Record<Level, string> = { high: 'Yuqori', medium: 'O‘rta', low: 'Past' }

export const EXPERT_STATUS_LABEL: Record<ExpertStatus, string> = {
  pending: 'Ko‘rib chiqilmagan',
  confirmed: 'Tasdiqlandi',
  rejected: 'Rad etildi',
  need_info: 'Qo‘shimcha ma’lumot kerak',
  sent_review: 'Tekshiruvga yuborildi',
}

export const DECISION_LABEL: Record<DecisionType, string> = {
  confirmed: 'Tasdiqlandi',
  rejected: 'Rad etildi',
  need_info: 'Qo‘shimcha ma’lumot kerak',
  sent_review: 'Tekshiruvga yuborildi',
}

export const DECISION_HINT: Record<DecisionType, string> = {
  confirmed: 'Xavf haqiqatan muhim',
  rejected: 'Model noto‘g‘ri belgilagan',
  need_info: 'Yetarli dalil yo‘q',
  sent_review: 'Qo‘shimcha tahlil talab qilinadi',
}

export const ALERT_STATUS_LABEL: Record<AlertStatus, string> = {
  new: 'Yangi',
  in_review: 'Ko‘rib chiqilmoqda',
  confirmed: 'Tasdiqlandi',
  rejected: 'Rad etildi',
  closed: 'Yopildi',
}

export const SIZE_LABEL: Record<string, string> = { small: 'Kichik', medium: 'O‘rta', large: 'Yirik' }

export const SOURCE_STATUS_LABEL: Record<string, string> = {
  active: 'Faol',
  delayed: 'Kechikkan',
  error: 'Xatolik',
  disabled: 'O‘chirilgan',
}

export const SOURCE_TYPE_LABEL: Record<string, string> = { api: 'API', db: 'Ma’lumotlar bazasi', file: 'Fayl' }

export const MODEL_STATUS_LABEL: Record<string, string> = {
  DRAFT: 'Qoralama',
  TESTING: 'Sinovda',
  APPROVED: 'Tasdiqlangan',
  ACTIVE: 'Faol',
  ARCHIVED: 'Arxivlangan',
}

export const JOB_STATUS_LABEL: Record<string, string> = {
  QUEUED: 'Navbatda',
  RUNNING: 'Bajarilmoqda',
  COMPLETED: 'Yakunlandi',
  FAILED: 'Xato bilan tugadi',
}

export const AUDIT_ACTION_LABEL: Record<string, string> = {
  'auth.login': 'Tizimga kirish',
  'auth.login_failed': 'Muvaffaqiyatsiz kirish urinishi',
  'auth.logout': 'Tizimdan chiqish',
  'subject.view': 'Subyekt kartasini ko‘rish',
  'subjects.export': 'Subyektlar ro‘yxatini eksport qilish',
  'decision.create': 'Ekspert qarori',
  'alert.update': 'Ogohlantirishni o‘zgartirish',
  'report.create': 'Hisobot yaratish',
  'report.export': 'Hisobotni yuklab olish',
  'import.upload': 'Fayl yuklash',
  'import.confirm': 'Importni tasdiqlash',
  'model.status': 'Model holatini o‘zgartirish',
  'model.recompute': 'Qayta hisoblash',
  'settings.thresholds': 'Xavf chegaralarini o‘zgartirish',
  'user.update': 'Foydalanuvchini o‘zgartirish',
  'data.seed': 'Namoyish ma’lumotlarini yuklash',
}

export const COMPONENT_LABEL: Record<string, string> = {
  dynamics: 'Faoliyat dinamikasi',
  sector: 'Sohaviy og‘ish',
  regional: 'Hududiy og‘ish',
  operational: 'Operatsion noodatiylik',
  network: 'Aloqadorlik',
  conflict: 'Ma’lumotlar ziddiyati',
  seasonal: 'Davriy og‘ish',
  anomaly: 'Anomaliya modeli',
}

export function levelFor(score: number, low: number, high: number): Level {
  if (score >= high) return 'high'
  if (score >= low) return 'medium'
  return 'low'
}
