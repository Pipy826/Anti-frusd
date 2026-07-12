<template>
  <section class="screen history-screen is-active">
    <h1>历史记录</h1>
    <p>保留最近10次挑战记录，优先展示服务端复盘</p>
    <div class="history-list">
      <button v-for="record in history" :key="record.id" class="history-card" @click="$emit('open', record)">
        <img class="history-card-img" :src="getScene(record.sceneId).image" alt="">
        <div class="history-card-content">
          <div class="history-card-body">
            <div class="history-card-info">
              <b>{{ record.sceneTitle }}</b>
              <small>{{ modeLabel(record.mode) }}</small>
            </div>
            <strong>{{ record.score }}<span>分</span></strong>
          </div>
          <time>{{ formatTime(record.createdAt) }}</time>
        </div>
      </button>
      <div v-if="!history.length" class="empty-state">暂无挑战记录</div>
    </div>
    <TabBar active="history" @go="$emit('go', $event)" />
  </section>
</template>

<script setup>
import TabBar from './TabBar.vue'
import { getScene } from '../data/scenes'

defineProps({
  history: { type: Array, required: true }
})
defineEmits(['open', 'go'])

function modeLabel(mode) {
  return { text: '文字模式', phone: '电话模式', video: '视频模式' }[mode] || '文字模式'
}

function formatTime(value) {
  const date = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>
