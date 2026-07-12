<template>
  <section class="screen review-screen is-active">
    <h2 class="page-title">挑战结束</h2>
    <div class="score-medal" :aria-label="`${review.score}分 ${review.level}`">
      <div class="medal-stars">★ ★ ★</div>
      <strong>{{ review.score }}<span>分</span></strong>
      <em>{{ review.level }}</em>
    </div>
    <p class="summary">{{ review.summary }}</p>
    <article v-if="dimensionItems.length" class="dimension-card">
      <h3>实战能力画像</h3>
      <div v-for="item in dimensionItems" :key="item.key" class="dimension-row">
        <span>{{ item.label }}</span>
        <i><em :style="{ width: `${item.value}%` }"></em></i>
        <b>{{ item.value }}</b>
      </div>
    </article>
    <article class="analysis-card">
      <h3><span class="ok">✓</span>正确应对</h3>
      <p v-for="item in review.correct" :key="item"><span>✓</span> {{ item }}</p>
      <hr>
      <h3><span class="warn">!</span>风险提醒</h3>
      <p v-for="item in review.risks" :key="item"><i>•</i> {{ item }}</p>
      <hr>
      <h3><span class="blue-dot">★</span>避坑指南</h3>
      <p v-for="item in review.tips" :key="item"><span>✓</span> {{ item }}</p>
      <template v-if="review.optimal_path">
        <hr>
        <h3><span class="blue-dot">★</span>最优应对路径</h3>
        <p><span>✓</span> {{ review.optimal_path }}</p>
      </template>
    </article>
    <div class="bottom-actions">
      <button class="primary" @click="$emit('retry')">重新挑战</button>
      <button class="outline" @click="$emit('change-scene')">换个场景</button>
    </div>
    <button class="detail-link" @click="$emit('detail')">查看复盘详情</button>
    <button class="detail-link" @click="saveShareCard">保存复盘分享卡片</button>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  review: { type: Object, required: true },
  scene: { type: Object, required: true }
})
defineEmits(['retry', 'change-scene', 'detail'])

const labels = {
  riskSpeed: '风险识别速度',
  privacyProtection: '信息保护程度',
  responseQuality: '应对话术有效性',
  lossPrevention: '止损效率'
}
const dimensionItems = computed(() =>
  Object.entries(props.review.dimensions || {}).map(([key, value]) => ({
    key,
    label: labels[key] || key,
    value
  }))
)

function saveShareCard() {
  const canvas = document.createElement('canvas')
  canvas.width = 900
  canvas.height = 1200
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const gradient = ctx.createLinearGradient(0, 0, 900, 1200)
  gradient.addColorStop(0, '#001735')
  gradient.addColorStop(1, '#126cff')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 900, 1200)

  ctx.fillStyle = '#f7faff'
  roundRect(ctx, 70, 80, 760, 1040, 36)
  ctx.fill()

  ctx.fillStyle = '#07112a'
  ctx.font = 'bold 52px Microsoft YaHei, sans-serif'
  ctx.fillText('反诈训练复盘', 120, 170)
  ctx.font = '28px Microsoft YaHei, sans-serif'
  ctx.fillStyle = '#53617a'
  ctx.fillText(props.scene.title, 120, 220)

  ctx.fillStyle = '#126cff'
  ctx.font = 'bold 120px Microsoft YaHei, sans-serif'
  ctx.fillText(String(props.review.score), 120, 370)
  ctx.font = 'bold 42px Microsoft YaHei, sans-serif'
  ctx.fillText(`${props.review.level} / 100`, 330, 352)

  ctx.fillStyle = '#07112a'
  ctx.font = 'bold 34px Microsoft YaHei, sans-serif'
  ctx.fillText('核心避坑点', 120, 470)
  ctx.font = '28px Microsoft YaHei, sans-serif'
  ctx.fillStyle = '#34415d'
  ;(props.review.risks || []).slice(0, 3).forEach((item, index) => {
    ctx.fillText(`${index + 1}. ${item}`, 120, 530 + index * 54)
  })

  ctx.fillStyle = '#07112a'
  ctx.font = 'bold 34px Microsoft YaHei, sans-serif'
  ctx.fillText('建议做法', 120, 740)
  ctx.font = '28px Microsoft YaHei, sans-serif'
  ctx.fillStyle = '#34415d'
  ;(props.review.tips || []).slice(0, 3).forEach((item, index) => {
    ctx.fillText(`${index + 1}. ${item}`, 120, 800 + index * 54)
  })

  ctx.fillStyle = '#ff4048'
  ctx.font = 'bold 38px Microsoft YaHei, sans-serif'
  ctx.fillText('遇到真实诈骗，请立即拨打 96110', 120, 1030)

  const link = document.createElement('a')
  link.download = `anti-fraud-review-${Date.now()}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.arcTo(x + width, y, x + width, y + height, radius)
  ctx.arcTo(x + width, y + height, x, y + height, radius)
  ctx.arcTo(x, y + height, x, y, radius)
  ctx.arcTo(x, y, x + width, y, radius)
  ctx.closePath()
}
</script>
