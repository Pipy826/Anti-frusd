<template>
  <section class="screen call-screen active-call-screen is-active">
    <StatusBar />
    <button class="icon-btn back" @click="$emit('back')">‹</button>
    <button class="dots">⠿</button>
    <div class="call-title">
      <h2>{{ scene.modeIdentity }}</h2>
      <p>{{ timer }}</p>
      <span>{{ state }}</span>
    </div>
    <div class="avatar-rings active"><span></span></div>
    <div class="wave"><i v-for="i in 8" :key="i"></i></div>
    <p class="record-tip">为了保障您的权益，通话可能会被录音</p>
    <div class="call-transcript">
      <p v-for="message in messages.slice(-3)" :key="`${message.role}-${message.text}`">
        <b>{{ message.role === 'user' ? '我' : scene.modeIdentity }}</b>{{ message.text }}
      </p>
    </div>
    <div class="call-quick">
      <button v-for="reply in scene.quickReplies.slice(0, 3)" :key="reply" :disabled="loading" @click="$emit('send', reply)">{{ reply }}</button>
    </div>
    <p v-if="error" class="inline-error">{{ error }}</p>
    <div class="call-tools">
      <button :class="{ muted: !asrSupported }" @click="asrSupported && $emit('listen')">♩<small>{{ asrSupported ? '语音' : '静音' }}</small></button>
      <button @click="$emit('send', scene.quickReplies[3] || scene.quickReplies[0])">⠿<small>键盘</small></button>
      <button>◕<small>免提</small></button>
    </div>
    <button class="hangup" @click="$emit('hangup')">☎<small>挂断</small></button>
  </section>
</template>

<script setup>
import StatusBar from './StatusBar.vue'

defineProps({
  scene: { type: Object, required: true },
  timer: { type: String, required: true },
  state: { type: String, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  asrSupported: { type: Boolean, default: false },
  messages: { type: Array, default: () => [] }
})
defineEmits(['back', 'send', 'listen', 'hangup'])
</script>
