<script setup lang="ts">
withDefaults(defineProps<{ lines?: number; height?: number; block?: boolean }>(), { lines: 3, height: 14, block: false })
</script>

<template>
  <div class="skeleton" aria-busy="true" aria-label="Yuklanmoqda">
    <div v-if="block" class="sk" :style="{ height: `${height}px` }" />
    <template v-else>
      <div v-for="i in lines" :key="i" class="sk" :style="{ height: `${height}px`, width: `${100 - ((i * 17) % 40)}%` }" />
    </template>
  </div>
</template>

<style scoped>
.skeleton { display: flex; flex-direction: column; gap: 10px; }

.sk {
  border-radius: 6px;
  background: linear-gradient(90deg, #eef3f8 0%, #f7fafd 40%, #eef3f8 80%);
  background-size: 800px 100%;
  animation: shimmer 1.3s linear infinite;
}
</style>
