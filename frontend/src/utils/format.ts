// O'zbek tilidagi formatlash: o'nlik vergul, minglik bo'shliq, oy nomlari.

const MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
const MONTHS_SHORT = ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avg', 'sen', 'okt', 'noy', 'dek']
const NBSP = ' '

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const fixed = Math.abs(v).toFixed(digits)
  const [int, frac] = fixed.split('.')
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP)
  const sign = v < 0 ? '−' : ''
  return sign + grouped + (frac ? ',' + frac : '')
}

export function signed(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return (v > 0 ? '+' : '') + num(v, digits)
}

export function pct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${num(v, digits)}%`
}

export function score(v: number | null | undefined): string {
  return num(v, v !== null && v !== undefined && Number.isInteger(v) ? 0 : 1)
}

function toDate(v: string | Date): Date {
  return v instanceof Date ? v : new Date(v)
}

export function date(v: string | null | undefined): string {
  if (!v) return '—'
  const d = toDate(v)
  if (Number.isNaN(d.getTime())) return '—'
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`
}

export function dateTime(v: string | null | undefined): string {
  if (!v) return '—'
  const d = toDate(v)
  if (Number.isNaN(d.getTime())) return '—'
  return `${date(v)}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function monthYear(v: string | null | undefined, short = false): string {
  if (!v) return '—'
  const d = toDate(v)
  const m = short ? MONTHS_SHORT[d.getMonth()] : MONTHS[d.getMonth()]
  return short ? `${m} ${String(d.getFullYear()).slice(2)}` : `${d.getFullYear()}-yil, ${m}`
}

export function periodRange(start?: string | null, end?: string | null): string {
  if (!start || !end) return '—'
  const s = toDate(start)
  const e = toDate(end)
  return `${MONTHS[s.getMonth()]} ${s.getFullYear()} — ${MONTHS[e.getMonth()]} ${e.getFullYear()}`
}

export function relative(v: string | null | undefined): string {
  if (!v) return '—'
  const diff = (Date.now() - toDate(v).getTime()) / 1000
  if (diff < 60) return 'hozirgina'
  if (diff < 3600) return `${Math.floor(diff / 60)} daqiqa oldin`
  if (diff < 86400) return `${Math.floor(diff / 3600)} soat oldin`
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} kun oldin`
  return date(v)
}

export function withUnit(v: number | null | undefined, unit: string): string {
  if (v === null || v === undefined) return 'Ma’lumot mavjud emas'
  switch (unit) {
    case '%':
      return pct(v, 1)
    case 'ta':
      return `${num(v, 0)} ta`
    case 'persentil':
      return `${num(v, 1)}-persentil`
    case 'indeks':
      return num(v, 3)
    case 'mln so‘m':
      return `${num(v, 1)} mln so‘m`
    case 'ming so‘m':
      return `${num(v, 1)} ming so‘m`
    default:
      return `${num(v, 2)} ${unit}`
  }
}
