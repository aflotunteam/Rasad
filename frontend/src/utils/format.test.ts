import { describe, expect, it } from 'vitest'
import { date, monthYear, num, pct, periodRange, score, signed, withUnit } from './format'
import { levelFor } from './labels'

const NBSP = ' '

describe('num', () => {
  it('o‘nlik vergul va minglik bo‘shliq bilan formatlaydi', () => {
    expect(num(5000)).toBe(`5${NBSP}000`)
    expect(num(1234567.891, 2)).toBe(`1${NBSP}234${NBSP}567,89`)
    expect(num(81.7, 1)).toBe('81,7')
  })

  it('manfiy sonlarga tipografik minus qo‘yadi', () => {
    expect(num(-65.8, 1)).toBe('−65,8')
  })

  it('bo‘sh qiymatlar uchun chiziqcha qaytaradi', () => {
    expect(num(null)).toBe('—')
    expect(num(undefined)).toBe('—')
    expect(num(Number.NaN)).toBe('—')
  })
})

describe('signed, pct, score', () => {
  it('musbat ta’sirga plyus qo‘yadi', () => {
    expect(signed(32.1)).toBe('+32,1')
    expect(signed(-4.5)).toBe('−4,5')
    expect(signed(0)).toBe('0,0')
  })

  it('foizni formatlaydi', () => {
    expect(pct(6.6)).toBe('6,6%')
    expect(pct(null)).toBe('—')
  })

  it('butun baholarda kasr qismini ko‘rsatmaydi', () => {
    expect(score(80)).toBe('80')
    expect(score(81.7)).toBe('81,7')
  })
})

describe('withUnit', () => {
  it('birlikka qarab formatlaydi', () => {
    expect(withUnit(-65.8, '%')).toBe('−65,8%')
    expect(withUnit(3, 'ta')).toBe('3 ta')
    expect(withUnit(0.714, 'indeks')).toBe('0,714')
    expect(withUnit(99.7, 'persentil')).toBe('99,7-persentil')
  })

  it('qiymat yo‘q bo‘lsa, buni ochiq aytadi', () => {
    expect(withUnit(null, '%')).toBe('Ma’lumot mavjud emas')
  })
})

describe('sanalar', () => {
  it('sanani kk.oo.yyyy ko‘rinishida beradi', () => {
    expect(date('2026-08-01')).toBe('01.08.2026')
    expect(date(null)).toBe('—')
    expect(date('noto‘g‘ri')).toBe('—')
  })

  it('oy nomlarini o‘zbek lotinida yozadi', () => {
    expect(monthYear('2026-08-01')).toBe('2026-yil, avgust')
    expect(monthYear('2026-09-01', true)).toBe('sen 26')
    expect(periodRange('2024-09-01', '2026-08-31')).toBe('sentabr 2024 — avgust 2026')
  })
})

describe('levelFor', () => {
  it('chegaralarni qo‘llaydi: past < 40 ≤ o‘rta < 70 ≤ yuqori', () => {
    expect(levelFor(39.9, 40, 70)).toBe('low')
    expect(levelFor(40, 40, 70)).toBe('medium')
    expect(levelFor(69.9, 40, 70)).toBe('medium')
    expect(levelFor(70, 40, 70)).toBe('high')
  })

  it('sozlangan chegaralarga amal qiladi', () => {
    expect(levelFor(65, 40, 60)).toBe('high')
  })
})
