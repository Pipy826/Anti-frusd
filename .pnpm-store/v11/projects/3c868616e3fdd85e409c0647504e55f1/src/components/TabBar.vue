<template>
  <nav class="tabbar">
    <button :class="['tab', { active: active === 'home' }]" @click="$emit('go', 'home')">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      首页
    </button>
    <button :class="['tab', { active: active === 'history' }]" @click="$emit('go', 'history')">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      历史记录
    </button>
    <button :class="['tab', { active: active === 'profile' }]" @click="$emit('go', 'profile')">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      我的
    </button>
  </nav>
</template>

<script setup>
defineProps({
  active: { type: String, required: true }
})
defineEmits(['go'])
</script>
