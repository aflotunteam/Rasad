<script setup lang="ts">
import { onMounted, ref } from 'vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { usersApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { Role, UserRow } from '@/types/api'
import { relative } from '@/utils/format'

const auth = useAuthStore()
const meta = useMetaStore()
const ui = useUiStore()
const users = ref<UserRow[] | null>(null)
const error = ref(false)

const MATRIX: [string, Record<Role, boolean>][] = [
  ['Bosh sahifa va subyektlar', { admin: true, analyst: true, manager: true, auditor: true }],
  ['Himoyalangan identifikatorni ko‘rish', { admin: true, analyst: true, manager: false, auditor: false }],
  ['Ekspert qarori', { admin: true, analyst: true, manager: false, auditor: false }],
  ['Ma’lumot importi', { admin: true, analyst: true, manager: false, auditor: false }],
  ['Modellar holatini o‘zgartirish', { admin: true, analyst: false, manager: false, auditor: false }],
  ['Xavf chegaralarini o‘zgartirish', { admin: true, analyst: false, manager: false, auditor: false }],
  ['Audit jurnali', { admin: true, analyst: false, manager: false, auditor: true }],
  ['Foydalanuvchilarni boshqarish', { admin: true, analyst: false, manager: false, auditor: false }],
]
const ROLES: Role[] = ['admin', 'analyst', 'manager', 'auditor']

async function load() {
  error.value = false
  try {
    users.value = await usersApi.list()
  } catch {
    error.value = true
  }
}

async function update(u: UserRow, patch: Partial<Pick<UserRow, 'role' | 'region_id' | 'is_active'>>) {
  try {
    const res = await usersApi.update(u.id, patch)
    Object.assign(u, res)
    ui.toast(`${u.full_name}: o‘zgarish saqlandi`, 'success')
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Saqlab bo‘lmadi', 'error')
    load()
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Foydalanuvchilar</h1>
        <p class="page-sub">Ruxsat rol, hudud va tashkilot bo‘yicha tekshiriladi (RBAC + ABAC). Tahlilchi faqat biriktirilgan hududni ko‘radi.</p>
      </div>
    </div>
    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <div v-else-if="!users" class="card card-pad"><LoadingSkeleton :lines="6" /></div>
    <template v-else>
      <div class="card">
        <table class="table">
          <thead><tr><th>Foydalanuvchi</th><th>Login</th><th>Rol</th><th>Hudud</th><th>Oxirgi kirish</th><th>Faol</th></tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td><b>{{ u.full_name }}</b></td>
              <td class="code">{{ u.username }}</td>
              <td>
                <select class="select sm" :value="u.role" :disabled="u.id === auth.user?.id" @change="update(u, { role: ($event.target as HTMLSelectElement).value as Role })">
                  <option v-for="(label, key) in meta.meta?.roles" :key="key" :value="key">{{ label }}</option>
                </select>
              </td>
              <td>
                <select class="select sm" :value="u.region_id ?? ''" @change="update(u, { region_id: ($event.target as HTMLSelectElement).value })">
                  <option value="">Barcha hududlar</option>
                  <option v-for="r in meta.meta?.regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </td>
              <td class="small muted">{{ relative(u.last_login_at) }}</td>
              <td><input type="checkbox" :checked="u.is_active" :disabled="u.id === auth.user?.id" :aria-label="`${u.full_name} faolligi`" @change="update(u, { is_active: ($event.target as HTMLInputElement).checked })" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card matrix">
        <div class="card-head"><div class="card-title">Ruxsatlar matritsasi</div></div>
        <table class="table">
          <thead><tr><th>Imkoniyat</th><th v-for="r in ROLES" :key="r">{{ meta.meta?.roles[r] }}</th></tr></thead>
          <tbody><tr v-for="[name, row] in MATRIX" :key="name"><td>{{ name }}</td><td v-for="r in ROLES" :key="r" :class="row[r] ? 'yes' : 'no'">{{ row[r] ? 'Ha' : '—' }}</td></tr></tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.select.sm { height: 30px; width: 190px; font-size: var(--fs-sm); }
.matrix { margin-top: var(--gap); }
.yes { color: var(--navy); font-weight: 650; }
.no { color: var(--muted-2); }
</style>
