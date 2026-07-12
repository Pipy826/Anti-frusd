<template>
  <section class="screen call-screen incoming-call-screen is-active">
    <button class="call-back-btn" @click="$emit('reject')">‹</button>
    <button class="call-menu-btn">⠿</button>
    <div class="caller-top call-fade-in">
      <h2>未知来电</h2>
      <p>{{ voice.phoneNumber || '188 **** 8888' }}</p>
      <span>{{ voice.location || '未知' }}</span>
    </div>
    <div class="avatar-rings call-ring-pulse"><span></span></div>
    <div class="caller-name call-fade-in-delay">
      <h3>{{ scene.modeIdentity }}</h3>
      <p>可能是诈骗电话</p>
    </div>
    <div class="answer-row call-slide-up">
      <button class="call-action red call-btn-bounce" @click="$emit('reject')">☎<small>拒绝</small></button>
      <button class="call-action green call-btn-bounce" @click="$emit('accept')">☎<small>接听</small></button>
    </div>
    <button class="sms call-fade-in-delay2">▰ 短信回复</button>
  </section>
</template>

<script setup>
defineProps({
  scene: { type: Object, required: true },
  voice: { type: Object, default: () => ({}) }
})
defineEmits(['reject', 'accept'])
</script>
