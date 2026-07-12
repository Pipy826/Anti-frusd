<template>
  <section class="screen profile-screen is-active">
    <header class="profile-top">
      <img :src="currentUser?.avatar || userSettings?.avatar || '/assets/profile-avatar.png'" alt="">
      <div>
        <h1>{{ currentUser?.nickname || userSettings?.user_name || '反诈小卫士' }}</h1>
        <p>练就火眼金睛，守护财产安全</p>
        <p>当前等级：<b>{{ userSettings?.level || 'Lv.1' }}</b></p>
      </div>
      <span class="profile-badge"></span>
    </header>
    <div class="menu-card">
      <button @click="$emit('go', 'game')"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></svg>我的成就 <i>›</i></button>
      <button @click="$emit('go', 'settings')"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68 1.65 1.65 0 0 0 9.09 3V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>账号设置 <i>›</i></button>
      <button @click="showGuide = true"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>使用说明 <i>›</i></button>
      <button @click="showFAQ = true"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>常见问题 <i>›</i></button>
      <button @click="showAbout = true"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>关于我们 <i>›</i></button>
      <button v-if="isAdmin()" @click="$emit('go', 'admin')"><svg class="menu-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>运营后台 <i>›</i></button>
    </div>
    <div class="profile-actions">
      <button class="clear" @click="$emit('clear')">清除本地记录</button>
      <button class="clear logout-btn" @click="handleLogout">退出登录</button>
    </div>
    <TabBar active="profile" @go="$emit('go', $event)" />

    <!-- 使用说明弹窗 -->
    <div v-if="showGuide" class="overlay-mask" @click="showGuide = false">
      <section class="overlay-dialog" @click.stop>
        <h3>使用说明</h3>
        <ol>
          <li>首页选择一个训练场景，点击"开始挑战"</li>
          <li>选择训练模式：文字、电话或视频</li>
          <li>与 AI 反诈角色进行模拟对话</li>
          <li>注意识别诈骗话术，避免泄露隐私或转账</li>
          <li>训练结束后查看复盘报告，了解风险点</li>
          <li>可在"我的成就"中查看徽章和积分</li>
        </ol>
        <button class="primary" @click="showGuide = false">知道了</button>
      </section>
    </div>

    <!-- 常见问题弹窗 -->
    <div v-if="showFAQ" class="overlay-mask" @click="showFAQ = false">
      <section class="overlay-dialog" @click.stop>
        <h3>常见问题</h3>
        <div class="faq-list">
          <details>
            <summary>训练数据会泄露吗？</summary>
            <p>本工具仅用于反诈科普学习，对话内容仅在本地或您的服务端存储，不会向第三方泄露。</p>
          </details>
          <details>
            <summary>AI 角色说的话是否真实？</summary>
            <p>所有对话内容均为虚构的诈骗模拟场景，旨在帮助用户识别常见诈骗套路，不具备真实操作指引。</p>
          </details>
          <details>
            <summary>如何报警？</summary>
            <p>如遇真实诈骗，请立即拨打全国反诈专线 96110，或前往就近派出所报案。</p>
          </details>
          <details>
            <summary>训练得分怎么计算？</summary>
            <p>系统根据您在对话中的表现，从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分。</p>
          </details>
        </div>
        <button class="primary" @click="showFAQ = false">关闭</button>
      </section>
    </div>

    <!-- 关于弹窗 -->
    <div v-if="showAbout" class="overlay-mask" @click="showAbout = false">
      <section class="overlay-dialog" @click.stop>
        <h3>关于我们</h3>
        <p><b>反诈话术陪练助手</b></p>
        <p>版本：v1.0</p>
        <p>本工具仅用于反诈科普学习，所有内容均为虚构。</p>
        <p>如遇真实诈骗，请立即拨打 <b>96110</b>。</p>
        <button class="primary" @click="showAbout = false">关闭</button>
      </section>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import TabBar from './TabBar.vue'
import { fetchUserSettings, getCurrentUser, isAdmin, logout } from '../services/api'

const emit = defineEmits(['clear', 'go', 'logout'])

const userSettings = ref(null)
const currentUser = ref(getCurrentUser())
const showGuide = ref(false)
const showFAQ = ref(false)
const showAbout = ref(false)

function handleLogout() {
  logout()
  emit('logout')
}

onMounted(async () => {
  try {
    const settings = await fetchUserSettings().catch(() => null)
    if (settings) userSettings.value = settings
  } catch {
    // 静默降级
  }
})
</script>

<style scoped>
.overlay-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.overlay-dialog {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  min-width: 280px;
}
.overlay-dialog h3 {
  margin: 0 0 16px;
  font-size: 18px;
  color: #333;
}
.overlay-dialog ol {
  margin: 0 0 16px;
  padding-left: 20px;
}
.overlay-dialog ol li {
  margin-bottom: 8px;
  font-size: 14px;
  color: #555;
}
.overlay-dialog p {
  margin: 8px 0;
  font-size: 14px;
  color: #555;
}
.faq-list details {
  margin-bottom: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}
.faq-list details summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}
.faq-list details p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}
</style>
