<script setup lang="ts">
import { CheckCircle2, Info, X, XCircle } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const ICON = { success: CheckCircle2, error: XCircle, info: Info }
</script>

<template>
  <div class="toast-host" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="`toast-${t.kind}`">
        <component :is="ICON[t.kind]" :size="18" />
        <span>{{ t.message }}</span>
        <button class="btn btn-ghost btn-icon btn-sm" aria-label="Yopish" @click="ui.dismiss(t.id)">
          <X :size="14" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 420px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px 10px 14px;
  background: var(--navy);
  color: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  font-size: var(--fs-md);
}

.toast span { flex: 1; }
.toast .btn { color: var(--on-dark-muted); }
.toast .btn:hover { background: rgba(255, 255, 255, 0.08); }
.toast-success svg:first-child { color: #6fd6a2; }
.toast-error svg:first-child { color: #f08f8c; }
.toast-info svg:first-child { color: var(--cyan); }

.toast-enter-active,
.toast-leave-active { transition: all var(--t) var(--ease); }
.toast-enter-from,
.toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
