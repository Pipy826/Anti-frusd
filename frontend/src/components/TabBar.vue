<template>
  <nav class="tabbar">
    <button :class="['tab', { active: active === 'home' }]" @click="$emit('go', 'home')"><span class="nav-icon nav-home"></span>首页</button>
    <button :class="['tab', { active: active === 'history' }]" @click="$emit('go', 'history')"><span class="nav-icon nav-clock"></span>历史记录</button>
    <button :class="['tab', { active: active === 'profile' }]" @click="$emit('go', 'profile')"><span class="nav-icon nav-user"></span>我的</button>
  </nav>
</template>

<script setup>
defineProps({
  active: { type: String, required: true }
})
defineEmits(['go'])
</script>
