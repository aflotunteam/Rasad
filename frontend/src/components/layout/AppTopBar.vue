<script setup lang="ts">
import { Bell, CalendarRange, ChevronDown, DatabaseZap, LogOut, UserRound } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import GlobalSearch from './GlobalSearch.vue'
import SyntheticBadge from '@/components/ui/SyntheticBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { periodRange, relative } from '@/utils/format'

defineProps<{ alertCount?: number }>()
const auth = useAuthStore()
const meta = useMetaStore()
const router = useRouter()
const menu = ref(false)

async function logout() {
  menu.value = false
  await auth.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <header class="topbar">
    <GlobalSearch />
    <div class="spacer" />
    <SyntheticBadge />
    <div class="tb-item" title="Tahlil davri">
      <CalendarRange :size="16" />
      <div>
        <div class="tb-label">Tahlil davri</div>
        <div class="tb-value">{{ periodRange(meta.meta?.period?.start, meta.meta?.period?.end) }}</div>
      </div>
    </div>
    <div class="tb-item tb-fresh" title="Faol manbalardan oxirgi yuklash vaqti">
      <DatabaseZap :size="16" />
      <div>
        <div class="tb-label">Ma’lumot yangiligi</div>
        <div class="tb-value">{{ relative(meta.meta?.data_freshness_at) }}</div>
      </div>
    </div>
    <RouterLink
      v-if="auth.can('alerts.read')"
      to="/alerts"
      class="btn btn-ghost btn-icon bell"
      :aria-label="`Ogohlantirishlar: ${alertCount ?? 0} ta yangi`"
    >
      <Bell :size="18" />
      <span v-if="alertCount" class="bell-dot num">{{ alertCount > 99 ? '99+' : alertCount }}</span>
    </RouterLink>
    <div class="profile" @focusout="(e) => !(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node) && (menu = false)">
      <button class="profile-btn" :aria-expanded="menu" aria-haspopup="menu" @click="menu = !menu">
        <span class="avatar"><UserRound :size="16" /></span>
        <span class="profile-text">
          <span class="profile-name">{{ auth.user?.full_name }}</span>
          <span class="profile-role">{{ auth.user?.role_label }}<template v-if="auth.user?.region_name"> · {{ auth.user.region_name }}</template></span>
        </span>
        <ChevronDown :size="15" />
      </button>
      <div v-if="menu" class="profile-menu" role="menu">
        <div class="pm-head">
          <div class="small muted">Tashkilot</div>
          <div class="small">{{ auth.user?.organization }}</div>
        </div>
        <button class="pm-item" role="menuitem" @click="logout"><LogOut :size="15" /> Tizimdan chiqish</button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 14px;
  height: var(--topbar-h);
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(1.4) blur(8px);
  border-bottom: 1px solid var(--border);
}

.tb-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  border-left: 1px solid var(--border);
  color: var(--muted);
}

.tb-label { font-size: 10.5px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted-2); }
.tb-value { font-size: var(--fs-sm); font-weight: 580; color: var(--navy); white-space: nowrap; }

.bell { position: relative; color: var(--navy); }

.bell-dot {
  position: absolute;
  top: 2px;
  right: -2px;
  min-width: 18px;
  height: 17px;
  padding: 0 4px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: var(--risk-high);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 13px;
  text-align: center;
}

.profile { position: relative; }

.profile-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 8px 5px 5px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  color: var(--muted);
}

.profile-btn:hover { background: var(--surface-2); }

.avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--navy);
  color: #fff;
}

.profile-text { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.25; max-width: 190px; }
.profile-name,
.profile-role { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.profile-name { font-size: var(--fs-sm); font-weight: 620; color: var(--navy); }
.profile-role { font-size: 11.5px; color: var(--muted); }

.profile-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 230px;
  padding: 6px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
}

.pm-head { padding: 8px 10px 10px; border-bottom: 1px solid var(--border); margin-bottom: 4px; }

.pm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: var(--fs-md);
}

.pm-item:hover { background: var(--surface-3); }

@media (max-width: 1540px) {
  .tb-fresh { display: none; }
}
</style>
