<template>
  <section class="screen detail-screen is-active">
    <header class="simple-head"><button class="icon-btn" @click="$emit('back')">‹</button><h2>复盘详情展开</h2></header>
    <div class="glass-panel">
      <div class="tabs">
        <button :class="{ active: tab === 'analysis' }" @click="tab = 'analysis'">复盘分析</button>
        <button :class="{ active: tab === 'record' }" @click="tab = 'record'">对话记录</button>
      </div>
      <template v-if="tab === 'analysis'">
        <article v-for="item in review.detail" :key="`${item.round}-${item.title}`">
          <h3><span :class="item.type === 'risk' ? 'warn' : 'ok'">{{ item.type === 'risk' ? '!' : '✓' }}</span>{{ item.type === 'risk' ? '风险探析分析' : '正确应对分析' }}</h3>
          <div class="inner-card">
            <b>第{{ item.round }}轮</b><span>{{ item.title }}</span>
            <em>你的回答：</em><p>“{{ item.user }}”</p>
            <em :class="{ 'green-text': item.type !== 'risk' }">分析：</em><p>{{ item.analysis }}</p>
            <template v-if="item.reference">
              <em class="green-text">参考话术：</em><p>{{ item.reference }}</p>
            </template>
            <button class="locate-round" @click="locateRound(item.round)">定位到第{{ item.round }}轮对话</button>
          </div>
        </article>
        <article>
          <h3><span class="blue-dot">★</span>总结与建议</h3>
          <ul><li v-for="tip in review.tips" :key="tip">{{ tip }}</li></ul>
        </article>
      </template>
      <div v-else class="detail-messages">
        <div
          v-for="message in decoratedMessages"
          :key="message.key"
          :ref="(el) => setMessageRef(message.round, el)"
          :class="['msg', message.role === 'user' ? 'me' : 'ai', { focused: targetRound === message.round && message.role === 'user' }]"
        >
          <img v-if="message.role !== 'user'" src="/assets/bot.png" alt="">
          <p>{{ message.text }}</p>
          <img v-if="message.role === 'user'" src="/assets/user.png" alt="">
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'

const props = defineProps({
  review: { type: Object, required: true },
  messages: { type: Array, default: () => [] }
})
defineEmits(['back'])
const tab = ref('analysis')
const targetRound = ref(0)
const messageRefs = new Map()

const decoratedMessages = computed(() => {
  let userRound = 0
  return props.messages.map((message, index) => {
    if (message.role === 'user') userRound += 1
    return { ...message, key: `${index}-${message.role}-${message.text}`, round: message.role === 'user' ? userRound : 0 }
  })
})

function setMessageRef(round, el) {
  if (!round || !el) return
  messageRefs.set(round, el)
}

async function locateRound(round) {
  targetRound.value = round
  tab.value = 'record'
  await nextTick()
  messageRefs.get(round)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
</script>
