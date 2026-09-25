<script setup lang="ts">
// Prompt §32: bo'sh va xato holatlar. Hech qachon bo'sh maydon qoldirilmaydi.
import {
  AlertOctagon,
  CloudOff,
  Database,
  FileClock,
  FileX2,
  Hourglass,
  Lock,
  PieChart,
  ServerCrash,
  type LucideIcon,
} from 'lucide-vue-next'
import { computed } from 'vue'

export type StateKind =
  | 'empty'
  | 'loading'
  | 'partial'
  | 'stale'
  | 'forbidden'
  | 'no-model'
  | 'report-pending'
  | 'import-error'
  | 'server-error'
  | 'network'

const props = withDefaults(defineProps<{ kind: StateKind; title?: string; message?: string; compact?: boolean }>(), {
  compact: false,
})
defineEmits<{ retry: [] }>()

const PRESETS: Record<StateKind, { icon: LucideIcon; title: string; message: string; tone: string }> = {
  empty: { icon: Database, title: 'Ma’lumot mavjud emas', message: 'Tanlangan shartlar bo‘yicha yozuv topilmadi.', tone: 'neutral' },
  loading: { icon: Hourglass, title: 'Yuklanmoqda', message: 'Ma’lumotlar tayyorlanmoqda…', tone: 'neutral' },
  partial: { icon: PieChart, title: 'Qisman ma’lumot', message: 'Ayrim manbalar hali yuklanmagan. Natija to‘liq emas.', tone: 'warn' },
  stale: { icon: FileClock, title: 'Ma’lumot eskirgan', message: 'Manba belgilangan muddatda yangilanmagan.', tone: 'warn' },
  forbidden: { icon: Lock, title: 'Ruxsat mavjud emas', message: 'Bu bo‘limni ko‘rish uchun sizning rolingizda ruxsat yo‘q.', tone: 'neutral' },
  'no-model': { icon: AlertOctagon, title: 'Model mavjud emas', message: 'Faol tasdiqlangan model topilmadi.', tone: 'warn' },
  'report-pending': { icon: Hourglass, title: 'Hisobot yaratilmoqda', message: 'Bir necha soniya kuting.', tone: 'neutral' },
  'import-error': { icon: FileX2, title: 'Import xatosi', message: 'Faylni qayta ishlab bo‘lmadi.', tone: 'danger' },
  'server-error': { icon: ServerCrash, title: 'Server xatosi', message: 'So‘rovni bajarib bo‘lmadi. Qayta urinib ko‘ring.', tone: 'danger' },
  network: { icon: CloudOff, title: 'Aloqa yo‘q', message: 'Server bilan bog‘lanib bo‘lmadi.', tone: 'danger' },
}

const preset = computed(() => PRESETS[props.kind])
</script>

<template>
  <div class="state" :class="[`tone-${preset.tone}`, { compact }]" role="status">
    <div class="state-icon"><component :is="preset.icon" :size="compact ? 18 : 22" /></div>
    <div class="state-title">{{ title ?? preset.title }}</div>
    <div class="state-msg">{{ message ?? preset.message }}</div>
    <div v-if="$slots.default" class="state-actions"><slot /></div>
    <button
      v-else-if="kind === 'server-error' || kind === 'network'"
      class="btn btn-sm state-actions"
      @click="$emit('retry')"
    >
      Qayta urinish
    </button>
  </div>
</template>

<style scoped>
.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 180px;
  padding: 28px 20px;
  text-align: center;
}

.state.compact { min-height: 110px; padding: 16px; }

.state-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: 4px;
  border-radius: 12px;
  background: var(--surface-3);
  color: var(--muted);
}

.compact .state-icon { width: 34px; height: 34px; border-radius: 10px; }
.tone-warn .state-icon { background: var(--risk-medium-bg); color: var(--risk-medium-text); }
.tone-danger .state-icon { background: var(--risk-high-bg); color: var(--risk-high); }
.state-title { font-weight: 620; color: var(--navy); }
.state-msg { max-width: 380px; color: var(--muted); font-size: var(--fs-md); }
.state-actions { margin-top: 8px; }
</style>
