<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ open: boolean; title: string; subtitle?: string; width?: number }>(), {
  width: 560,
})
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
let lastFocus: HTMLElement | null = null

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      lastFocus = document.activeElement as HTMLElement
      document.addEventListener('keydown', onKey)
      await nextTick()
      panel.value?.focus()
    } else {
      document.removeEventListener('keydown', onKey)
      lastFocus?.focus?.()
    }
  },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="open" class="drawer-root">
        <div class="drawer-backdrop" @click="emit('close')" />
        <aside
          ref="panel"
          class="drawer"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
          :style="{ width: `${width}px` }"
        >
          <header class="drawer-head">
            <div>
              <h2 class="drawer-title">{{ title }}</h2>
              <p v-if="subtitle" class="drawer-sub">{{ subtitle }}</p>
            </div>
            <button class="btn btn-ghost btn-icon" aria-label="Yopish" @click="emit('close')"><X :size="18" /></button>
          </header>
          <div class="drawer-body"><slot /></div>
          <footer v-if="$slots.footer" class="drawer-foot"><slot name="footer" /></footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-root { position: fixed; inset: 0; z-index: 500; }

.drawer-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(11, 31, 58, 0.32);
}

.drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  max-width: calc(100vw - 40px);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  box-shadow: var(--shadow-lg);
  outline: none;
}

.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--border);
}

.drawer-title { font-size: var(--fs-xl); }
.drawer-sub { margin-top: 3px; color: var(--muted); font-size: var(--fs-md); }
.drawer-body { flex: 1; overflow: auto; padding: 18px 22px 24px; }

.drawer-foot {
  padding: 12px 22px;
  border-top: 1px solid var(--border);
  background: var(--surface-2);
}

.drawer-enter-active,
.drawer-leave-active { transition: opacity var(--t-slow) var(--ease); }
.drawer-enter-active .drawer,
.drawer-leave-active .drawer { transition: transform var(--t-slow) var(--ease); }
.drawer-enter-from,
.drawer-leave-to { opacity: 0; }
.drawer-enter-from .drawer,
.drawer-leave-to .drawer { transform: translateX(32px); }
</style>
