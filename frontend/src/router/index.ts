import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    perm?: string
    public?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true, title: 'Kirish' } },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('@/pages/DashboardPage.vue'), meta: { title: 'Bosh sahifa', perm: 'dashboard' } },
      { path: 'regions', name: 'regions', component: () => import('@/pages/RegionsPage.vue'), meta: { title: 'Hududlar', perm: 'dashboard' } },
      { path: 'regions/:id', name: 'region', component: () => import('@/pages/RegionsPage.vue'), meta: { title: 'Hududlar', perm: 'dashboard' } },
      { path: 'subjects', name: 'subjects', component: () => import('@/pages/SubjectsPage.vue'), meta: { title: 'Subyektlar', perm: 'subjects' } },
      { path: 'subjects/:code', name: 'subject', component: () => import('@/pages/SubjectDetailPage.vue'), meta: { title: 'Subyekt kartasi', perm: 'subjects' } },
      { path: 'analytics', name: 'analytics', component: () => import('@/pages/AnalyticsPage.vue'), meta: { title: 'Tahlillar', perm: 'dashboard' } },
      { path: 'relations', name: 'relations', component: () => import('@/pages/RelationsPage.vue'), meta: { title: 'Aloqadorliklar', perm: 'subjects' } },
      { path: 'alerts', name: 'alerts', component: () => import('@/pages/AlertsPage.vue'), meta: { title: 'Ogohlantirishlar', perm: 'alerts.read' } },
      { path: 'reports', name: 'reports', component: () => import('@/pages/ReportsPage.vue'), meta: { title: 'Hisobotlar', perm: 'reports' } },
      { path: 'data-sources', name: 'data-sources', component: () => import('@/pages/DataSourcesPage.vue'), meta: { title: 'Ma’lumot manbalari', perm: 'data_sources' } },
      { path: 'models', name: 'models', component: () => import('@/pages/ModelsPage.vue'), meta: { title: 'Modellar', perm: 'models.read' } },
      { path: 'audit', name: 'audit', component: () => import('@/pages/AuditPage.vue'), meta: { title: 'Audit', perm: 'audit' } },
      { path: 'users', name: 'users', component: () => import('@/pages/UsersPage.vue'), meta: { title: 'Foydalanuvchilar', perm: 'users' } },
      { path: 'settings', name: 'settings', component: () => import('@/pages/SettingsPage.vue'), meta: { title: 'Sozlamalar', perm: 'settings' } },
      { path: 'forbidden', name: 'forbidden', component: () => import('@/pages/ForbiddenPage.vue'), meta: { title: 'Ruxsat mavjud emas' } },
      { path: ':pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/NotFoundPage.vue'), meta: { title: 'Sahifa topilmadi' } },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.restore()
  if (to.meta.public) {
    return auth.isAuthenticated && to.name === 'login' ? { name: 'dashboard' } : true
  }
  if (!auth.isAuthenticated) return { name: 'login', query: to.fullPath !== '/' ? { next: to.fullPath } : {} }
  if (to.meta.perm && !auth.can(to.meta.perm)) return { name: 'forbidden' }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — RASAD` : 'RASAD'
})
