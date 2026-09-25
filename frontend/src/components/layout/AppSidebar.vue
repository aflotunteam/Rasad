<script setup lang="ts">
import {
  Bell,
  BrainCircuit,
  ChartNoAxesCombined,
  Database,
  FileText,
  LayoutDashboard,
  Map,
  ScrollText,
  Settings,
  Share2,
  UsersRound,
  Building2,
  type LucideIcon,
} from 'lucide-vue-next'
import { computed } from 'vue'
import BrandMark from './BrandMark.vue'
import { useAuthStore } from '@/stores/auth'

defineProps<{ alertCount?: number }>()
const auth = useAuthStore()

interface NavItem {
  to: string
  name: string
  label: string
  icon: LucideIcon
  perm: string
  badge?: boolean
}

const groups: { title: string; items: NavItem[] }[] = [
  {
    title: 'Tahlil',
    items: [
      { to: '/', name: 'dashboard', label: 'Bosh sahifa', icon: LayoutDashboard, perm: 'dashboard' },
      { to: '/regions', name: 'regions', label: 'Hududlar', icon: Map, perm: 'dashboard' },
      { to: '/subjects', name: 'subjects', label: 'Subyektlar', icon: Building2, perm: 'subjects' },
      { to: '/analytics', name: 'analytics', label: 'Tahlillar', icon: ChartNoAxesCombined, perm: 'dashboard' },
      { to: '/relations', name: 'relations', label: 'Aloqadorliklar', icon: Share2, perm: 'subjects' },
      { to: '/alerts', name: 'alerts', label: 'Ogohlantirishlar', icon: Bell, perm: 'alerts.read', badge: true },
      { to: '/reports', name: 'reports', label: 'Hisobotlar', icon: FileText, perm: 'reports' },
    ],
  },
  {
    title: 'Boshqaruv',
    items: [
      { to: '/data-sources', name: 'data-sources', label: 'Ma’lumot manbalari', icon: Database, perm: 'data_sources' },
      { to: '/models', name: 'models', label: 'Modellar', icon: BrainCircuit, perm: 'models.read' },
      { to: '/audit', name: 'audit', label: 'Audit', icon: ScrollText, perm: 'audit' },
      { to: '/users', name: 'users', label: 'Foydalanuvchilar', icon: UsersRound, perm: 'users' },
      { to: '/settings', name: 'settings', label: 'Sozlamalar', icon: Settings, perm: 'settings' },
    ],
  },
]

const visible = computed(() =>
  groups.map((g) => ({ ...g, items: g.items.filter((i) => auth.can(i.perm)) })).filter((g) => g.items.length),
)
</script>

<template>
  <aside class="sidebar" aria-label="Asosiy navigatsiya">
    <RouterLink to="/" class="brand" aria-label="RASAD bosh sahifa">
      <BrandMark :size="36" />
      <div>
        <div class="brand-name">RASAD</div>
        <div class="brand-sub">Iqtisodiy xavf signallari tahlili</div>
      </div>
    </RouterLink>

    <nav class="nav">
      <div v-for="g in visible" :key="g.title" class="nav-group">
        <div class="nav-title">{{ g.title }}</div>
        <RouterLink
          v-for="item in g.items"
          :key="item.name"
          :to="item.to"
          class="nav-item"
          :class="{ active: item.to === '/' ? $route.name === 'dashboard' : $route.path.startsWith(item.to) }"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.8" />
          <span>{{ item.label }}</span>
          <span v-if="item.badge && alertCount" class="nav-badge num" :aria-label="`${alertCount} ta yangi ogohlantirish`">
            {{ alertCount > 99 ? '99+' : alertCount }}
          </span>
        </RouterLink>
      </div>
    </nav>

    <div class="principle">
      <div class="principle-title">Asosiy tamoyil</div>
      <p>RASAD aybni aniqlamaydi. U qaysi holat birinchi navbatda ekspert tahlilini talab qilishini va nima sababdan ekanini ko‘rsatadi.</p>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar-w);
  display: flex;
  flex-direction: column;
  background: var(--navy);
  color: var(--on-dark);
  z-index: 50;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  height: 72px;
  padding: 0 18px;
  color: #fff;
  text-decoration: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.brand:hover { text-decoration: none; }
.brand-name { font-size: 18px; font-weight: 750; letter-spacing: 0.14em; }
.brand-sub { margin-top: 1px; font-size: 11px; color: var(--on-dark-muted); }

.nav { flex: 1; overflow-y: auto; padding: 12px 12px; }
.nav-group + .nav-group { margin-top: 14px; }

.nav-title {
  padding: 6px 10px;
  font-size: 10.5px;
  font-weight: 650;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #6f84a3;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  height: 38px;
  padding: 0 10px;
  margin: 1px 0;
  border-radius: 9px;
  color: #c3d0e2;
  font-size: var(--fs-md);
  font-weight: 520;
  text-decoration: none;
  transition: background var(--t-fast) var(--ease), color var(--t-fast) var(--ease);
}

.nav-item:hover { background: rgba(255, 255, 255, 0.06); color: #fff; text-decoration: none; }

.nav-item.active {
  background: linear-gradient(90deg, rgba(33, 109, 243, 0.95), rgba(33, 109, 243, 0.78));
  color: #fff;
  box-shadow: 0 4px 14px -6px rgba(33, 109, 243, 0.8);
}

.nav-item svg { flex-shrink: 0; }
.nav-item span:first-of-type { flex: 1; }

.nav-badge {
  min-width: 22px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(217, 83, 79, 0.95);
  color: #fff;
  font-size: 11px;
  font-weight: 650;
  line-height: 20px;
  text-align: center;
}

.principle {
  margin: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.03);
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--on-dark-muted);
}

.principle-title {
  margin-bottom: 4px;
  font-size: 10.5px;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--cyan);
}
</style>
