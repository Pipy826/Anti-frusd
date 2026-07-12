<template>
  <section class="screen game-screen is-active">
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
        <h3>成长记录</h3>
        <p><span>最高得分</span><b>{{ myScore }}</b></p>
        <p><span>平均得分</span><b>{{ avgScore }}</b></p>
        <p><span>训练次数</span><b>{{ history.length }}</b></p>
        <p><span>已解锁场景</span><b>{{ completed.size }} / {{ scenes.length }}</b></p>
        <button class="primary small" @click="showRank = !showRank">查看排名</button>
        <p v-if="showRank" class="rank-info"><span>当前水平</span><b>{{ rankText }}</b></p>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  scenes: { type: Array, required: true },
  history: { type: Array, default: () => [] }
})
defineEmits(['go'])

const myScore = computed(() => {
  const scores = props.history.map((item) => Number(item.score) || 0).filter((s) => s > 0)
  return scores.length ? Math.max(...scores) : 0
})
const avgScore = computed(() => {
  const scores = props.history.map((item) => Number(item.score) || 0).filter((s) => s > 0)
  return scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
})
const completed = computed(() => new Set(props.history.map((item) => item.sceneId)))
const showRank = ref(false)
const rankText = computed(() => {
  if (!myScore.value) return '待挑战'
  const threshold = 75
  if (myScore.value >= threshold) return '领先'
  if (myScore.value >= threshold - 15) return '接近达标'
  return '继续加油'
})
const badges = computed(() => [
  { icon: '盾', name: '初识风险', desc: '完成 1 次训练', earned: props.history.length >= 1 },
  { icon: '核', name: '核验达人', desc: '得分达到 85', earned: props.history.some((item) => (Number(item.score) || 0) >= 85) },
  { icon: '拒', name: '果断拒绝', desc: '完成 3 个场景', earned: completed.value.size >= 3 },
  { icon: '榜', name: '持续进步', desc: '完成 5 次训练', earned: props.history.length >= 5 }
])

function unlocked(index) {
  return index === 0 || props.history.length >= index
}
</script>

