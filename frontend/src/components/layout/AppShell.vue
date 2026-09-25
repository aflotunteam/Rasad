<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppTopBar from './AppTopBar.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { alertsApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'

const meta = useMetaStore()
const auth = useAuthStore()
const alertCount = ref(0)
const failed = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

async function refreshAlerts() {
  if (!auth.can('alerts.read')) return
  try {
    const page = await alertsApi.list({ status: 'new', page_size: 1 })
    alertCount.value = page.total
  } catch {
    /* hisoblagich ikkinchi darajali: xato UI ni to'xtatmaydi */
  }
}

async function init() {
  failed.value = false
  try {
    await meta.load()
    refreshAlerts()
  } catch {
    failed.value = true
  }
}

onMounted(() => {
  init()
  timer = setInterval(refreshAlerts, 60_000)
  window.addEventListener('rasad:alerts-changed', refreshAlerts)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('rasad:alerts-changed', refreshAlerts)
})
</script>

<template>
  <div class="shell">
    <a href="#main" class="skip-link">Asosiy mazmunga o‘tish</a>
    <AppSidebar :alert-count="alertCount" />
    <div class="shell-main">
      <AppTopBar :alert-count="alertCount" />
      <main id="main" tabindex="-1">
        <StateBlock v-if="failed" kind="server-error" class="card" style="margin: 28px" @retry="init" />
        <RouterView v-else-if="meta.meta" v-slot="{ Component, route }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell { min-height: 100%; }
.shell-main { margin-left: var(--sidebar-w); min-height: 100vh; }
main { outline: none; }

.skip-link {
  position: absolute;
  left: -9999px;
  top: 8px;
  z-index: 100;
  padding: 8px 12px;
  background: var(--blue);
  color: #fff;
  border-radius: 8px;
}

.skip-link:focus { left: 12px; }
</style>
