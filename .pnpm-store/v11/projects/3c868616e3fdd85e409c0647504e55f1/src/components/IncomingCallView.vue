<template>
  <section class="screen call-screen incoming-call-screen is-active">
    <StatusBar />
    <button class="icon-btn back" @click="$emit('reject')">‹</button>
    <button class="dots">⠿</button>
    <div class="caller-top">
      <h2>未知来电</h2>
      <p>{{ voice.phoneNumber || '188 **** 8888' }}</p>
      <span>{{ voice.location || '未知' }}</span>
    </div>
    <div class="avatar-rings"><span></span></div>
    <div class="caller-name">
      <h3>{{ scene.modeIdentity }}</h3>
      <p>可能是诈骗电话</p>
    </div>
    <div class="answer-row">
      <button class="call-action red" @click="$emit('reject')">☎<small>拒绝</small></button>
      <button class="call-action green" @click="$emit('accept')">☎<small>接听</small></button>
    </div>
    <button class="sms">▰ 短信回复</button>
  </section>
</template>

<script setup>
import StatusBar from './StatusBar.vue'

defineProps({
  scene: { type: Object, required: true },
  voice: { type: Object, default: () => ({}) }
})
defineEmits(['reject', 'accept'])
</script>
