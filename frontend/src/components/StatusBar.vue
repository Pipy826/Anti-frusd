<template>
  <div class="status"><b>{{ time }}</b><span>▮▮▮ WiFi ▱</span></div>
</template>

<script setup>
defineProps({
  time: { type: String, default: '9:41' }
})
</script>
