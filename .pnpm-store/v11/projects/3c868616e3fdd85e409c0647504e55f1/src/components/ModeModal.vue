<template>
  <div class="modal is-open" aria-hidden="false">
    <div class="modal-card">
      <button class="close" @click="$emit('close')">×</button>
      <h2>请选择体验方式</h2>
      <p>不同模式，不同体验</p>
      <label :class="['mode', { active: mode === 'text' }]">
        <span class="bubble">•••</span><b>文字聊天模式<small>推荐新手，轻松上手</small></b>
        <input v-model="mode" type="radio" value="text">
      </label>
      <label :class="['mode', { active: mode === 'phone' }]">
        <span class="phone">☎</span><b>电话通话模式<small>沉浸体验，识别话术</small></b>
        <input v-model="mode" type="radio" value="phone">
      </label>
      <label :class="['mode', { active: mode === 'video' }]">
        <span>▣</span><b>视频通话模式<small>接触面更广，更加真实</small></b>
        <input v-model="mode" type="radio" value="video">
      </label>
      <label class="check"><input type="checkbox" checked> 不再提醒</label>
      <div class="modal-actions">
        <button class="ghost" @click="$emit('close')">取消</button>
        <button class="primary" @click="$emit('start', mode)">开始体验</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  scene: { type: Object, required: true }
})
defineEmits(['close', 'start'])
const mode = ref('text')
</script>
