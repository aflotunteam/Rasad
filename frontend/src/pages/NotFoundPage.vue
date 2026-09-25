<script setup lang="ts">
import StateBlock from '@/components/ui/StateBlock.vue'
</script>

<template>
  <div class="page">
    <div class="card">
      <StateBlock kind="empty" title="Sahifa topilmadi" message="Manzil noto‘g‘ri yoki sahifa o‘chirilgan.">
        <RouterLink to="/" class="btn btn-sm">Bosh sahifaga qaytish</RouterLink>
      </StateBlock>
    </div>
  </div>
</template>
