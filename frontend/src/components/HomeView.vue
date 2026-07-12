<template>
  <section class="screen screen-home is-active">
    <StatusBar />
    <div class="notice"><span>!</span><p>{{ brand.complianceNotice }}</p></div>
    <header class="hero">
      <div>
        <h1>{{ brand.mainTitle }}</h1>
        <p>{{ brand.subtitle }}</p>
      </div>
      <img :src="brand.logoUrl || '/assets/hero-shield.png'" alt="">
    </header>

    <div class="home-stats">
      <div class="home-stat">
        <strong>{{ stats.total }}</strong>
        <span>训练次数</span>
      </div>
      <div class="home-stat">
        <strong>{{ stats.bestScore }}</strong>
        <span>最高分</span>
      </div>
      <div class="home-stat">
        <strong>{{ stats.scenesCount }}</strong>
        <span>场景总数</span>
      </div>
    </div>

    <div class="quick-actions">
      <button class="quick-action" @click="$emit('go', 'game')">
        <span class="qa-icon">🏆</span> 成就徽章
      </button>
      <button class="quick-action" @click="scrollToTop">
        <span class="qa-icon">📋</span> 全部场景
      </button>
    </div>

    <div class="scene-list-header">
      <h3>训练场景</h3>
      <span>{{ scenes.length }} 个场景</span>
    </div>

    <div class="scene-list" ref="sceneListRef">
      <article v-for="scene in scenes" :key="scene.id" class="scene-card">
        <img class="scene-thumb" :src="scene.image" alt="">
        <div class="scene-info">
          <h2>{{ scene.title }}</h2>
          <p class="stars">难度：<b>{{ scene.difficulty }}</b><small v-if="scene.category">{{ scene.category }}</small></p>
          <p>{{ scene.description }}</p>
        </div>
        <button class="primary small scene-start" @click="$emit('select-scene', scene)">开始挑战</button>
      </article>
    </div>

    <p class="brand-footer">{{ brand.orgName }} · {{ brand.copyrightText }}</p>
    <TabBar active="home" @go="$emit('go', $event)" />
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import StatusBar from './StatusBar.vue'
import TabBar from './TabBar.vue'

const props = defineProps({
  scenes: { type: Array, required: true },
  brand: { type: Object, required: true }
})
defineEmits(['select-scene', 'go'])

const sceneListRef = ref(null)

const stats = computed(() => {
  const saved = localStorage.getItem('anti_fraud_history')
  const history = saved ? JSON.parse(saved) : []
  const scores = history.map(h => h.score).filter(Boolean)
  const bestScore = scores.length ? Math.max(...scores) : '--'
  return {
    total: history.length || 0,
    bestScore: bestScore,
    scenesCount: props.scenes.length
  }
})

function scrollToTop() {
  sceneListRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>