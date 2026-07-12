<template>
  <section class="screen chat-screen is-active">
    <StatusBar />
    <header class="chat-head">
      <button class="icon-btn" @click="$emit('back')">‹</button>
      <h2>{{ scene.title }}</h2>
      <button class="danger" @click="$emit('end')">结束挑战</button>
    </header>
    <div class="time-pill">10:21</div>
    <div class="risk-panel">
      <div>
        <span>个人信息泄露风险</span>
        <b>{{ risk.privacy }}%</b>
        <i><em :style="{ width: `${risk.privacy}%` }"></em></i>
      </div>
      <div>
        <span>财产损失风险</span>
        <b>{{ risk.property }}%</b>
        <i><em :style="{ width: `${risk.property}%` }"></em></i>
      </div>
      <p v-if="risk.warning">{{ risk.warning }}</p>
    </div>
    <div ref="messageBox" class="messages">
      <div v-for="(message, index) in messages" :key="`${index}-${message.text}`" :class="['msg', message.role === 'user' ? 'me' : 'ai']">
        <img v-if="message.role !== 'user'" src="/assets/bot.png" alt="">
        <p>
          <template v-for="(part, partIndex) in tokenizeMessage(message.text)" :key="`${index}-${partIndex}`">
            <span :class="{ 'message-token': part.type === 'token' }">{{ part.text }}</span>
          </template>
          <button v-if="message.role !== 'user'" class="bubble-speak" @click="$emit('speak', message.text)">▶</button>
        </p>
        <img v-if="message.role === 'user'" src="/assets/user.png" alt="">
      </div>
      <div v-if="loading" class="typing">对方正在输入...</div>
    </div>
    <p v-if="error" class="inline-error">{{ error }}</p>
    <div class="quick">
      <button v-for="reply in visibleQuickReplies" :key="reply" @click="draft = reply">{{ reply }}</button>
    </div>
    <form :class="['composer', { compact: !asrSupported }]" @submit.prevent="submit">
      <button v-if="asrSupported" type="button" class="round" @click="$emit('listen')">♩</button>
      <input v-model="draft" placeholder="输入您的回复..." autocomplete="off">
      <button class="primary send">发送</button>
      <button type="button" class="round">＋</button>
    </form>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import StatusBar from './StatusBar.vue'

const props = defineProps({
  scene: { type: Object, required: true },
  messages: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  risk: { type: Object, required: true },
  quickReplies: { type: Array, default: () => [] },
  asrSupported: { type: Boolean, default: false }
})
const emit = defineEmits(['back', 'send', 'end', 'speak', 'listen'])
const draft = ref('')
const messageBox = ref(null)
const visibleQuickReplies = computed(() => (props.quickReplies.length ? props.quickReplies : props.scene.quickReplies).slice(0, 4))

watch(() => props.messages.length, async () => {
  await nextTick()
  if (messageBox.value) messageBox.value.scrollTop = messageBox.value.scrollHeight
})

function submit() {
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
}

function tokenizeMessage(text = '') {
  return String(text)
    .split(/(【[^】]+】)/g)
    .filter(Boolean)
    .map((part) => ({ text: part, type: /^【[^】]+】$/.test(part) ? 'token' : 'text' }))
}
</script>
