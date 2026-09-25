import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  kind: 'success' | 'error' | 'info'
  message: string
}

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<Toast[]>([])
  const sidebarCollapsed = ref(false)
  // Global hudud filtri: xaritadan tanlanadi va bosh sahifa, ro'yxatlarga ta'sir qiladi.
  const region = ref<string | null>(null)
  let seq = 0

  function toast(message: string, kind: Toast['kind'] = 'info', timeout = 4200) {
    const id = ++seq
    toasts.value.push({ id, kind, message })
    setTimeout(() => dismiss(id), timeout)
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, toast, dismiss, sidebarCollapsed, region }
})
