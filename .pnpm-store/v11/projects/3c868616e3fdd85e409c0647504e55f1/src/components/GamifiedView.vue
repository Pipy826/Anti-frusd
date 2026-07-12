<template>
  <section class="screen game-screen is-active">
    <StatusBar />
    <header class="simple-head">
      <button class="icon-btn" @click="$emit('go', 'profile')">‹</button>
      <h2>闯关与 PK</h2>
      <span></span>
    </header>

    <div class="game-scroll">
      <section class="admin-panel">
        <h3>答题闯关</h3>
        <p v-for="(scene, index) in scenes" :key="scene.id">
          <span>第 {{ index + 1 }} 关 · {{ scene.title }}</span>
          <b>{{ unlocked(index) ? '已解锁' : '待解锁' }}</b>
        </p>
      </section>

      <section class="admin-panel badges">
        <h3>成就徽章</h3>
        <div class="badge-grid">
          <article v-for="badge in badges" :key="badge.name" :class="{ earned: badge.earned }">
            <strong>{{ badge.icon }}</strong>
            <b>{{ badge.name }}</b>
            <span>{{ badge.desc }}</span>
          </article>
        </div>
      </section>

      <section class="admin-panel pk-panel">
        <h3>多人 PK</h3>
        <p><span>我的最近得分</span><b>{{ myScore }}</b></p>
        <p><span>同组平均</span><b>{{ peerScore }}</b></p>
        <p><span>当前排名</span><b>{{ rankText }}</b></p>
        <button class="primary small" @click="simulatePk">刷新 PK 榜</button>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import StatusBar from './StatusBar.vue'

const props = defineProps({
  scenes: { type: Array, required: true },
  history: { type: Array, default: () => [] }
})
defineEmits(['go'])

const peerScore = ref(76)
const myScore = computed(() => props.history[0]?.score || 0)
const completed = computed(() => new Set(props.history.map((item) => item.sceneId)))
const rankText = computed(() => {
  if (!myScore.value) return '待挑战'
  return myScore.value >= peerScore.value ? '领先小组' : '继续追赶'
})
const badges = computed(() => [
  { icon: '盾', name: '初识风险', desc: '完成 1 次训练', earned: props.history.length >= 1 },
  { icon: '核', name: '核验达人', desc: '得分达到 85', earned: props.history.some((item) => item.score >= 85) },
  { icon: '拒', name: '果断拒绝', desc: '完成 3 个场景', earned: completed.value.size >= 3 },
  { icon: '榜', name: 'PK 领先', desc: '最近得分高于小组平均', earned: myScore.value >= peerScore.value && myScore.value > 0 }
])

function unlocked(index) {
  return index === 0 || props.history.length >= index
}

function simulatePk() {
  peerScore.value = 68 + Math.floor(Math.random() * 24)
}
</script>

