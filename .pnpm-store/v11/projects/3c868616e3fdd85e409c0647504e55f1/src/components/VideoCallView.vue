<template>
  <section class="screen video-screen is-active">
    <StatusBar time="10:28" />
    <div class="video-title"><p>{{ timer }}</p><h2>{{ scene.modeIdentity }}</h2><span>通话中</span></div>
    <div class="digital-human">
      <img class="agent" src="/assets/agent-video.png?v=20260712" alt="">
      <span class="mouth-sync"></span>
    </div>
    <div class="side-wave"><i v-for="i in 5" :key="i"></i></div>
    <div class="video-actions">
      <button>♩<small>静音</small></button>
      <button class="hangup" @click="$emit('hangup')">☎<small>挂断</small></button>
      <button>▣<small>摄像头</small></button>
    </div>
    <div class="video-quick">
      <button v-for="reply in scene.quickReplies.slice(0, 3)" :key="reply" :disabled="loading" @click="$emit('send', reply)">{{ reply }}</button>
    </div>
    <div class="warm-tip"><img src="/assets/hero-shield.png" alt=""><p><b>温馨提示</b><br>客服不会要求您提供银行卡密码、短信验证码等敏感信息，请谨防诈骗。</p></div>
  </section>
</template>

<script setup>
import StatusBar from './StatusBar.vue'

defineProps({
  scene: { type: Object, required: true },
  timer: { type: String, required: true },
  loading: { type: Boolean, default: false }
})
defineEmits(['hangup', 'send'])
</script>
