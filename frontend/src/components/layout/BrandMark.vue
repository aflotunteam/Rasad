<script setup lang="ts">
withDefaults(defineProps<{ size?: number; dark?: boolean }>(), { size: 34, dark: true })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" aria-hidden="true">
    <rect width="40" height="40" rx="10" :fill="dark ? '#13294A' : '#0B1F3A'" />
    <circle cx="20" cy="20" r="12" fill="none" stroke="#38BDF8" stroke-width="1.6" opacity="0.9" />
    <circle cx="20" cy="20" r="7" fill="none" stroke="#216DF3" stroke-width="1.8" />
    <path d="M20 20 L29.5 12.5" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round" />
    <circle cx="20" cy="20" r="2.2" fill="#fff" />
    <circle cx="27.4" cy="14.2" r="1.7" fill="#38BDF8" />
  </svg>
</template>
