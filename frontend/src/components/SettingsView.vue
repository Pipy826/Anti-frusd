<template>
  <section class="screen settings-screen is-active">
    <header class="settings-header">
      <button class="settings-back-btn" @click="$emit('go', 'profile')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <h2>账号设置</h2>
      <span></span>
    </header>

    <div class="settings-content">
      <!-- 头像与基本信息 -->
      <section class="settings-card">
        <h3>基本信息</h3>
        <div class="avatar-row">
          <img :src="settingsForm.avatar || '/assets/profile-avatar.png'" alt="头像" class="avatar-img" />
          <button class="avatar-change-btn" @click="changeAvatar">更换头像</button>
        </div>
        <label>
          <span>昵称</span>
          <input v-model="settingsForm.userName" placeholder="输入昵称" />
        </label>
        <div class="level-info">
          <span>当前等级</span>
          <b :class="levelBadgeClass">{{ settingsForm.level }}</b>
        </div>
        <div class="points-info">
          <span>累计积分</span>
          <b>{{ userStats?.totalPoints ?? settingsForm.totalPoints ?? 0 }}</b>
        </div>
      </section>

      <!-- 训练统计 -->
      <section class="settings-card">
        <h3>我的统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <strong>{{ userStats?.totalSessions ?? 0 }}</strong>
            <span>训练次数</span>
          </div>
          <div class="stat-item">
            <strong>{{ userStats?.todaySessions ?? 0 }}</strong>
            <span>今日训练</span>
          </div>
          <div class="stat-item">
            <strong>{{ userStats?.averageScore ?? '--' }}</strong>
            <span>平均得分</span>
          </div>
          <div class="stat-item">
            <strong>{{ userStats?.highRiskSessions ?? 0 }}</strong>
            <span>高危预警</span>
          </div>
        </div>
      </section>

      <!-- 偏好设置 -->
      <section class="settings-card">
        <h3>偏好设置</h3>

        <div class="setting-row">
          <div class="setting-label">
            <span>通知提醒</span>
            <small>开启训练提醒和风险提示推送</small>
          </div>
          <button
            :class="['toggle-btn', { on: settingsForm.notificationEnabled }]"
            @click="settingsForm.notificationEnabled = !settingsForm.notificationEnabled"
          >
            {{ settingsForm.notificationEnabled ? '开启' : '关闭' }}
          </button>
        </div>

        <div class="setting-row">
          <div class="setting-label">
            <span>语音播报</span>
            <small>训练过程中自动播放语音回复</small>
          </div>
          <button
            :class="['toggle-btn', { on: settingsForm.voiceEnabled }]"
            @click="settingsForm.voiceEnabled = !settingsForm.voiceEnabled"
          >
            {{ settingsForm.voiceEnabled ? '开启' : '关闭' }}
          </button>
        </div>

        <div class="setting-row">
          <div class="setting-label">
            <span>主题模式</span>
            <small>切换界面颜色方案</small>
          </div>
          <div class="theme-selector">
            <button
              :class="['theme-btn', { active: settingsForm.theme === 'light' }]"
              @click="settingsForm.theme = 'light'"
            >浅色</button>
            <button
              :class="['theme-btn', { active: settingsForm.theme === 'dark' }]"
              @click="settingsForm.theme = 'dark'"
            >深色</button>
          </div>
        </div>
      </section>

      <!-- 关于 -->
      <section class="settings-card">
        <h3>关于</h3>
        <p><span>应用版本</span><b>v1.0</b></p>
        <p><span>反诈热线</span><b>96110</b></p>
        <p><span>使用说明</span><b>本工具仅用于反诈科普学习</b></p>
      </section>

      <!-- 保存按钮 -->
      <button class="settings-save-btn" :disabled="saving" @click="saveSettings">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>

      <p v-if="saveMsg" :class="saveMsgType === 'error' ? 'save-msg-error' : 'save-msg-ok'">
        {{ saveMsg }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { fetchUserSettings, updateUserSettings, fetchUserStats } from '../services/api'

defineEmits(['go'])

const settingsForm = ref({
  userName: '反诈小卫士',
  level: 'Lv.1',
  avatar: '/assets/profile-avatar.png',
  totalPoints: 0,
  theme: 'light',
  notificationEnabled: true,
  voiceEnabled: true
})
const userStats = ref(null)
const saving = ref(false)
const saveMsg = ref('')
const saveMsgType = ref('ok')

const levelBadgeClass = computed(() => {
  const level = settingsForm.value.level
  if (level.includes('Lv.1')) return 'level-badge level-1'
  if (level.includes('Lv.2')) return 'level-badge level-2'
  if (level.includes('Lv.3')) return 'level-badge level-3'
  return 'level-badge level-4'
})

function changeAvatar() {
  const avatars = [
    '/assets/profile-avatar.png',
    '/assets/hero-shield.png',
    '/assets/bot.png',
    '/assets/shield.png'
  ]
  const current = settingsForm.value.avatar
  const idx = avatars.indexOf(current)
  settingsForm.value.avatar = avatars[(idx + 1) % avatars.length]
}

async function loadSettings() {
  try {
    const [settings, stats] = await Promise.all([
      fetchUserSettings().catch(() => null),
      fetchUserStats().catch(() => null)
    ])
    if (settings) {
      settingsForm.value = {
        ...settingsForm.value,
        userName: settings.user_name || settingsForm.value.userName,
        level: settings.level || settingsForm.value.level,
        avatar: settings.avatar || settingsForm.value.avatar,
        totalPoints: settings.total_points ?? settingsForm.value.totalPoints,
        theme: settings.theme || settingsForm.value.theme,
        notificationEnabled: settings.notification_enabled ?? settingsForm.value.notificationEnabled,
        voiceEnabled: settings.voice_enabled ?? settingsForm.value.voiceEnabled
      }
    }
    if (stats) {
      userStats.value = stats
    }
  } catch {
    // 静默降级，使用默认值
  }
}

async function saveSettings() {
  saving.value = true
  saveMsg.value = ''
  try {
    const payload = {
      user_name: settingsForm.value.userName,
      level: settingsForm.value.level,
      avatar: settingsForm.value.avatar,
      theme: settingsForm.value.theme,
      notification_enabled: settingsForm.value.notificationEnabled,
      voice_enabled: settingsForm.value.voiceEnabled
    }
    await updateUserSettings(payload)
    saveMsg.value = '设置已保存'
    saveMsgType.value = 'ok'
  } catch (err) {
    saveMsg.value = err.message || '保存失败，请重试'
    saveMsgType.value = 'error'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>
