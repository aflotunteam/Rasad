import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/services/api'
import { getToken, setToken } from '@/services/http'
import type { User } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(getToken())
  const ready = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const role = computed(() => user.value?.role ?? null)
  const regionScope = computed(() => (user.value?.role === 'analyst' ? user.value.region_id : null))

  function can(perm: string): boolean {
    return !!user.value?.permissions.includes(perm)
  }

  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    token.value = res.token
    setToken(res.token)
    user.value = res.user
    ready.value = true
  }

  async function restore() {
    if (!token.value) {
      ready.value = true
      return
    }
    try {
      user.value = await authApi.me()
    } catch {
      clear()
    } finally {
      ready.value = true
    }
  }

  function clear() {
    token.value = null
    user.value = null
    setToken(null)
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      /* sessiya allaqachon tugagan bo'lishi mumkin */
    }
    clear()
  }

  return { user, token, ready, isAuthenticated, role, regionScope, can, login, restore, logout, clear }
})
