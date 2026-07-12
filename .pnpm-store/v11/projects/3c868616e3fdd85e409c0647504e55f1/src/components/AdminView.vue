<template>
  <section class="admin-screen admin-pc-screen">
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <img :src="brand.logoUrl || '/assets/hero-shield.png'" alt="">
        <div>
          <strong>{{ brand.mainTitle || '反诈话术陪练助手' }}</strong>
          <span>管理后台</span>
        </div>
      </div>

      <nav class="admin-nav" aria-label="管理端导航">
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="{ active: page === item.key }"
          @click="switchPage(item.key)"
        >
          <span>{{ item.icon }}</span>{{ item.label }}
        </button>
      </nav>

      <div class="admin-sidebar-footer">
        <a :href="exportHref" download>导出报表</a>
        <small>v1.0 管理端</small>
      </div>
    </aside>

    <main class="admin-main">
      <header class="admin-topbar">
        <button class="admin-menu-btn" title="返回前台" @click="$emit('go', 'profile')">‹</button>
        <div>
          <h1>{{ currentNav.label }}</h1>
          <p>{{ currentNav.desc }}</p>
        </div>
        <div class="admin-top-actions">
          <label class="admin-search">
            <input v-model="keyword" :placeholder="currentNav.search || '搜索场景/用户/关键词...'" />
            <span>⌕</span>
          </label>
          <button class="admin-icon-action" title="刷新" @click="reload">刷新</button>
          <a class="admin-export-btn" :href="exportHref" download>导出</a>
          <div class="admin-user">
            <img src="/assets/profile-avatar.png" alt="">
            <span>管理员</span>
          </div>
        </div>
      </header>

      <p v-if="error" class="admin-error">{{ error }}</p>

      <section v-if="page === 'dashboard'" class="admin-content">
        <div class="admin-stat-grid">
          <article v-for="metric in dashboardMetrics" :key="metric.label" class="admin-stat-card">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.hint }}</small>
          </article>
        </div>

        <div class="admin-layout-grid">
          <section class="admin-card admin-wide">
            <div class="admin-card-head">
              <h2>体验趋势</h2>
              <div class="admin-segment">
                <button :class="{ active: range === 'today' }" @click="range = 'today'">今日</button>
                <button :class="{ active: range === '7d' }" @click="range = '7d'">近7日</button>
                <button :class="{ active: range === '30d' }" @click="range = '30d'">近30日</button>
              </div>
            </div>
            <div class="admin-line-chart">
              <p v-if="!trendPoints.length" class="admin-empty">暂无真实趋势数据</p>
              <i v-for="point in trendPoints" :key="point.left" :style="{ left: point.left, bottom: point.bottom }"></i>
            </div>
          </section>

          <section class="admin-card">
            <div class="admin-card-head">
              <h2>热门场景 TOP5</h2>
            </div>
            <div class="admin-rank-list">
              <p v-if="!sceneRank.length" class="admin-empty">暂无真实排行数据</p>
              <p v-for="(item, index) in sceneRank" :key="item.title">
                <b>{{ index + 1 }}</b>
                <span>{{ item.title }}</span>
                <i><em :style="{ width: rankPercent(item.total) }"></em></i>
                <strong>{{ item.total }}</strong>
              </p>
            </div>
          </section>

          <section class="admin-card admin-wide">
            <div class="admin-card-head">
              <h2>最新对话记录</h2>
              <button @click="switchPage('conversations')">查看全部</button>
            </div>
            <table class="admin-table">
              <thead>
                <tr><th>会话</th><th>场景</th><th>模式</th><th>得分</th><th>风险</th><th>时间</th></tr>
              </thead>
              <tbody>
                <tr v-if="!conversations.length">
                  <td colspan="6" class="admin-empty-cell">暂无真实对话记录</td>
                </tr>
                <tr v-for="item in conversations.slice(0, 5)" :key="item.sessionId">
                  <td>{{ shortId(item.sessionId) }}</td>
                  <td>{{ item.sceneTitle }}</td>
                  <td>{{ modeLabel(item.mode) }}</td>
                  <td><b :class="scoreClass(item.score)">{{ item.score || '-' }}</b></td>
                  <td>{{ riskLabel(item) }}</td>
                  <td>{{ dateLabel(item.createdAt) }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="admin-card">
            <div class="admin-card-head">
              <h2>风险预警</h2>
            </div>
            <div class="admin-alert-list">
              <p v-for="alert in riskAlerts" :key="alert.title">
                <span :class="alert.level">{{ alert.badge }}</span>
                <b>{{ alert.title }}</b>
                <small>{{ alert.desc }}</small>
              </p>
            </div>
          </section>
        </div>
      </section>

      <section v-if="page === 'scenes'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card"><span>全部场景</span><strong>{{ editableScenes.length }}</strong><small>训练内容库</small></article>
          <article class="admin-stat-card"><span>已上线</span><strong>{{ activeSceneCount }}</strong><small>前台可见</small></article>
          <article class="admin-stat-card"><span>未上线</span><strong>{{ editableScenes.length - activeSceneCount }}</strong><small>草稿或停用</small></article>
          <article class="admin-stat-card"><span>场景标签</span><strong>{{ sceneCategories.length }}</strong><small>分类覆盖</small></article>
        </div>

        <section class="admin-card">
          <div class="admin-card-head">
            <h2>场景管理</h2>
            <button class="admin-primary-btn" @click="openSceneEditor()">新增场景</button>
          </div>
          <div class="admin-filters">
            <select v-model="sceneStatus">
              <option value="">全部状态</option>
              <option value="active">已上线</option>
              <option value="inactive">未上线</option>
            </select>
            <select v-model="sceneCategory">
              <option value="">全部标签</option>
              <option v-for="category in sceneCategories" :key="category" :value="category">{{ category }}</option>
            </select>
            <button @click="resetSceneFilters">重置</button>
          </div>
          <table class="admin-table scene-table">
            <thead>
              <tr><th>场景信息</th><th>标签</th><th>难度</th><th>状态</th><th>版本</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-if="!filteredScenes.length">
                <td colspan="6" class="admin-empty-cell">暂无真实场景数据</td>
              </tr>
              <tr v-for="scene in filteredScenes" :key="scene.id">
                <td>
                  <div class="scene-cell">
                    <img :src="scene.image || '/assets/hero-shield.png'" alt="">
                    <div><b>{{ scene.title }}</b><small>{{ scene.description }}</small></div>
                  </div>
                </td>
                <td><span class="admin-tag">{{ scene.category || '未分类' }}</span></td>
                <td>{{ scene.difficulty }}</td>
                <td>
                  <button :class="['switch-btn', { on: scene.active !== false }]" @click="toggleScene(scene)">
                    {{ scene.active === false ? '未上线' : '已上线' }}
                  </button>
                </td>
                <td>v{{ scene.promptVersion || 1 }}</td>
                <td>
                  <button class="text-btn" @click="openSceneEditor(scene)">编辑</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </section>

      <section v-if="page === 'sceneEdit'" class="admin-content">
        <section class="admin-card">
          <div class="admin-card-head">
            <h2>{{ editingScene.id ? '编辑场景' : '新增场景' }}</h2>
            <button @click="switchPage('scenes')">返回列表</button>
          </div>
          <div class="scene-editor-grid">
            <label>场景 ID<input v-model="editingScene.id" :disabled="Boolean(editingOriginalId)" placeholder="例如 telecom"></label>
            <label>场景名称<input v-model="editingScene.title"></label>
            <label>短标题<input v-model="editingScene.shortTitle"></label>
            <label>分类标签<input v-model="editingScene.category"></label>
            <label>难度<input v-model="editingScene.difficulty"></label>
            <label>图标路径<input v-model="editingScene.image"></label>
            <label class="span-2">简介<textarea v-model="editingScene.description"></textarea></label>
            <label class="span-2">代入引导<textarea v-model="editingScene.intro"></textarea></label>
            <label class="span-2">角色 Prompt<textarea v-model="editingScene.role"></textarea></label>
            <label class="span-2">评分 Prompt<textarea v-model="editingScene.scoringPrompt"></textarea></label>
            <label class="span-2">首句话术<textarea v-model="editingScene.firstMessage"></textarea></label>
            <label class="span-2">快捷回复，每行一条<textarea v-model="quickReplyText"></textarea></label>
            <label class="span-2">兜底回复，每行一条<textarea v-model="fallbackReplyText"></textarea></label>
          </div>
          <div class="admin-form-actions">
            <button class="admin-secondary-btn" @click="switchPage('scenes')">取消</button>
            <button class="admin-primary-btn" @click="saveEditingScene">保存场景</button>
          </div>
        </section>
      </section>

      <section v-if="page === 'conversations'" class="admin-content conversation-layout">
        <aside class="admin-card conversation-filter">
          <h2>筛选条件</h2>
          <label>场景
            <select v-model="conversationScene">
              <option value="">全部场景</option>
              <option v-for="scene in editableScenes" :key="scene.id" :value="scene.title">{{ scene.title }}</option>
            </select>
          </label>
          <label>模式
            <select v-model="conversationMode">
              <option value="">全部模式</option>
              <option value="text">文字模式</option>
              <option value="phone">电话模式</option>
              <option value="video">视频模式</option>
            </select>
          </label>
          <label>风险等级
            <select v-model="conversationRisk">
              <option value="">全部等级</option>
              <option value="high">高风险</option>
              <option value="middle">中风险</option>
              <option value="low">低风险</option>
            </select>
          </label>
          <button class="admin-primary-btn" @click="reload">查询</button>
          <a class="admin-secondary-link" :href="exportHref" download>导出数据</a>
        </aside>

        <section class="admin-card conversation-list">
          <div class="admin-card-head">
            <h2>共 {{ filteredConversations.length }} 条记录</h2>
          </div>
          <p v-if="!filteredConversations.length" class="admin-empty">暂无真实对话记录</p>
          <button
            v-for="item in filteredConversations"
            :key="item.sessionId"
            :class="{ active: activeConversation?.sessionId === item.sessionId }"
            @click="activeConversation = item"
          >
            <div><b>{{ item.sceneTitle }}</b><small>{{ shortId(item.sessionId) }} · {{ modeLabel(item.mode) }}</small></div>
            <strong :class="scoreClass(item.score)">{{ item.score || '-' }}分</strong>
            <span>{{ riskLabel(item) }}</span>
          </button>
        </section>

        <section class="admin-card conversation-detail">
          <div class="admin-card-head">
            <h2>对话详情</h2>
            <a :href="exportHref" download>导出对话</a>
          </div>
          <div v-if="activeConversation" class="conversation-summary">
            <p><span>会话ID</span><b>{{ activeConversation.sessionId }}</b></p>
            <p><span>场景</span><b>{{ activeConversation.sceneTitle }}</b></p>
            <p><span>模式</span><b>{{ modeLabel(activeConversation.mode) }}</b></p>
            <p><span>风险</span><b>{{ activeConversation.riskPrivacy }} / {{ activeConversation.riskProperty }}</b></p>
          </div>
          <div class="message-timeline">
            <p v-if="!activeConversationMessages.length" class="admin-empty">请选择一条真实对话记录</p>
            <article v-for="(message, index) in activeConversationMessages" :key="`${message.role}-${index}`" :class="message.role">
              <span>{{ message.role === 'user' ? '用户' : 'AI' }}</span>
              <p>{{ message.text }}</p>
            </article>
          </div>
        </section>
      </section>

      <section v-if="page === 'audit'" class="admin-content">
        <div class="admin-layout-grid">
          <section class="admin-card">
            <div class="admin-card-head">
              <h2>敏感词库</h2>
            </div>
            <div class="term-form">
              <input v-model="newTerm" placeholder="输入需要拦截或提示的词">
              <button class="admin-primary-btn" @click="saveTerm">添加</button>
            </div>
            <div class="term-list">
              <p v-for="term in safetyTerms" :key="term.id">
                <span>{{ term.term }}</span>
                <b>{{ term.direction }} / {{ term.action }}</b>
              </p>
            </div>
          </section>

          <section class="admin-card admin-wide">
            <div class="admin-card-head">
              <h2>待关注内容</h2>
            </div>
            <table class="admin-table">
              <thead>
                <tr><th>会话</th><th>场景</th><th>风险等级</th><th>摘要</th><th>处理</th></tr>
              </thead>
              <tbody>
                <tr v-if="!highRiskConversations.length">
                  <td colspan="5" class="admin-empty-cell">暂无真实高风险内容</td>
                </tr>
                <tr v-for="item in highRiskConversations" :key="item.sessionId">
                  <td>{{ shortId(item.sessionId) }}</td>
                  <td>{{ item.sceneTitle }}</td>
                  <td><span :class="['risk-chip', riskLevel(item)]">{{ riskLabel(item) }}</span></td>
                  <td>{{ item.messages?.[0]?.text || '暂无摘要' }}</td>
                  <td><button class="text-btn" @click="activeConversation = item; switchPage('conversations')">查看</button></td>
                </tr>
              </tbody>
            </table>
          </section>
        </div>
      </section>

      <section v-if="page === 'stats'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card"><span>API 成功率</span><strong>{{ metrics.apiSuccessRate || 0 }}%</strong><small>近一小时</small></article>
          <article class="admin-stat-card"><span>平均响应</span><strong>{{ metrics.averageResponseMs || 0 }}ms</strong><small>接口耗时</small></article>
          <article class="admin-stat-card"><span>模型失败</span><strong>{{ metrics.llmFailureCount || 0 }}</strong><small>降级次数</small></article>
          <article class="admin-stat-card"><span>活跃会话</span><strong>{{ metrics.activeSessions || 0 }}</strong><small>当前在线</small></article>
        </div>
        <section class="admin-card">
          <div class="admin-card-head"><h2>四维平均分</h2></div>
          <div class="dimension-bars">
            <p v-if="!dimensionItems.length" class="admin-empty">暂无真实维度统计</p>
            <p v-for="item in dimensionItems" :key="item.key">
              <span>{{ item.label }}</span>
              <i><em :style="{ width: `${Number(item.value) || 0}%` }"></em></i>
              <b>{{ item.value }}</b>
            </p>
          </div>
        </section>
      </section>

      <section v-if="page === 'settings'" class="admin-content">
        <div class="admin-layout-grid">
          <section class="admin-card admin-wide">
            <div class="admin-card-head"><h2>品牌展示</h2></div>
            <div class="scene-editor-grid">
              <label>Logo 地址<input v-model="brandDraft.logoUrl"></label>
              <label>单位名称<input v-model="brandDraft.orgName"></label>
              <label>主标题<input v-model="brandDraft.mainTitle"></label>
              <label>副标题<input v-model="brandDraft.subtitle"></label>
              <label class="span-2">合规提示<textarea v-model="brandDraft.complianceNotice"></textarea></label>
              <label class="span-2">版权信息<input v-model="brandDraft.copyrightText"></label>
            </div>
            <div class="admin-form-actions">
              <button class="admin-primary-btn" @click="saveBrand">保存配置</button>
            </div>
          </section>

          <section class="admin-card">
            <div class="admin-card-head"><h2>模型状态</h2></div>
            <div class="model-list">
              <p v-for="model in modelStatus" :key="model.provider || model.name">
                <span>{{ model.provider || model.name }}</span>
                <b :class="{ ok: model.available !== false }">{{ model.available === false ? '不可用' : '可用' }}</b>
              </p>
              <p v-if="!modelStatus.length"><span>模型状态</span><b>暂无真实状态数据</b></p>
            </div>
          </section>
        </div>
      </section>
    </main>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createAdminScene,
  createSafetyTerm,
  fetchAdminDashboard,
  fetchAdminMetrics,
  fetchAdminModelStatus,
  fetchAdminScenes,
  fetchConversations,
  fetchSafetyTerms,
  reportFrontendError,
  updateAdminScene,
  updateBrand
} from '../services/api'

const props = defineProps({
  brand: { type: Object, required: true }
})
const emit = defineEmits(['go', 'brand-updated'])

const navItems = [
  { key: 'dashboard', label: '数据看板', icon: 'D', desc: '您好，管理员！欢迎回来', search: '搜索指标/场景...' },
  { key: 'scenes', label: '场景管理', icon: 'S', desc: '管理训练场景内容，支持新增、编辑与上下线', search: '搜索场景名称/标签...' },
  { key: 'conversations', label: '对话管理', icon: 'C', desc: '查看用户对话详情，支持内容检索与导出', search: '搜索用户ID/场景/关键词...' },
  { key: 'audit', label: '内容审核', icon: 'A', desc: '处理高风险对话内容，维护敏感词库', search: '搜索违规摘要/敏感词...' },
  { key: 'stats', label: '数据统计', icon: 'T', desc: '查看接口、模型与训练效果的细粒度统计', search: '搜索统计项...' },
  { key: 'settings', label: '系统设置', icon: 'G', desc: '配置品牌展示、模型状态与安全策略', search: '搜索配置项...' }
]

const page = ref(hashPage())
const range = ref('today')
const keyword = ref('')
const error = ref('')
const dashboard = ref(emptyDashboard())
const metrics = ref({})
const editableScenes = ref([])
const conversations = ref([])
const safetyTerms = ref([])
const modelStatus = ref([])
const brandDraft = ref({ ...props.brand })
const newTerm = ref('')
const sceneStatus = ref('')
const sceneCategory = ref('')
const conversationScene = ref('')
const conversationMode = ref('')
const conversationRisk = ref('')
const activeConversation = ref(null)
const editingScene = ref(defaultNewScene())
const editingOriginalId = ref('')
const quickReplyText = ref('')
const fallbackReplyText = ref('')

const labels = {
  riskSpeed: '风险识别速度',
  privacyProtection: '信息保护程度',
  responseQuality: '应对话术有效性',
  lossPrevention: '止损效率'
}

const currentNav = computed(() => navItems.find((item) => item.key === page.value) || navItems[0])
const exportHref = computed(() => `/api/admin/export.xlsx?tenant=${encodeURIComponent(currentTenant())}`)
const activeSceneCount = computed(() => editableScenes.value.filter((scene) => scene.active !== false).length)
const sceneCategories = computed(() => [...new Set(editableScenes.value.map((scene) => scene.category).filter(Boolean))])
const sceneRank = computed(() => dashboard.value.sceneRank || [])
const maxRankTotal = computed(() => Math.max(1, ...sceneRank.value.map((item) => Number(item.total) || 0)))
const dimensionItems = computed(() =>
  Object.entries(dashboard.value.averageDimensions || {}).map(([key, value]) => ({
    key,
    label: labels[key] || key,
    value
  }))
)
const dashboardMetrics = computed(() => [
  { label: '累计体验人次', value: dashboard.value.totalSessions || 0, hint: '平台训练总量' },
  { label: '今日活跃人数', value: dashboard.value.todayActive || 0, hint: '今日新增会话' },
  { label: '平均反诈得分', value: `${dashboard.value.averageScore || 0} 分`, hint: '已完成训练平均值' },
  { label: '高危行为触发率', value: `${dashboard.value.highRiskTriggerRate || 0}%`, hint: `${dashboard.value.highRiskCount || 0} 次高危` }
])
const trendPoints = computed(() => {
  const bucketCount = range.value === 'today' ? 12 : range.value === '7d' ? 7 : 30
  const now = Date.now()
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const start = range.value === 'today' ? todayStart.getTime() : now - bucketCount * 24 * 60 * 60 * 1000
  const span = Math.max(1, now - start)
  const buckets = Array.from({ length: bucketCount }, () => 0)

  conversations.value.forEach((item) => {
    const time = Date.parse(item.createdAt || '')
    if (!Number.isFinite(time) || time < start || time > now) return
    const index = Math.min(bucketCount - 1, Math.floor(((time - start) / span) * bucketCount))
    buckets[index] += 1
  })

  const max = Math.max(...buckets)
  if (!max) return []
  return buckets.map((value, index, list) => ({
    left: `${(index / (list.length - 1)) * 100}%`,
    bottom: `${Math.max(8, Math.round((value / max) * 88))}%`
  }))
})
const filteredScenes = computed(() => {
  const term = keyword.value.trim().toLowerCase()
  return editableScenes.value.filter((scene) => {
    const matchKeyword = !term || [scene.title, scene.category, scene.description].some((value) => String(value || '').toLowerCase().includes(term))
    const matchStatus = !sceneStatus.value || (sceneStatus.value === 'active' ? scene.active !== false : scene.active === false)
    const matchCategory = !sceneCategory.value || scene.category === sceneCategory.value
    return matchKeyword && matchStatus && matchCategory
  })
})
const filteredConversations = computed(() => {
  const term = keyword.value.trim().toLowerCase()
  return conversations.value.filter((item) => {
    const matchKeyword = !term || [item.sessionId, item.sceneTitle, ...(item.messages || []).map((message) => message.text)].some((value) => String(value || '').toLowerCase().includes(term))
    const matchScene = !conversationScene.value || item.sceneTitle === conversationScene.value
    const matchMode = !conversationMode.value || item.mode === conversationMode.value
    const matchRisk = !conversationRisk.value || riskLevel(item) === conversationRisk.value
    return matchKeyword && matchScene && matchMode && matchRisk
  })
})
const highRiskConversations = computed(() => conversations.value.filter((item) => riskLevel(item) !== 'low'))
const activeConversationMessages = computed(() => activeConversation.value?.messages || [])
const riskAlerts = computed(() => [
  { level: 'danger', badge: '高危', title: '高风险会话待复核', desc: `${highRiskConversations.value.length} 条记录需要关注` },
  { level: 'warning', badge: '中危', title: '模型降级与接口失败', desc: `${metrics.value?.llmFailureCount || 0} 次模型降级` },
  { level: 'info', badge: '提示', title: '内容安全规则', desc: `${safetyTerms.value.length} 条敏感词规则启用` }
])

watch(() => props.brand, (next) => {
  brandDraft.value = { ...next }
})

onMounted(() => {
  window.addEventListener('hashchange', syncHashPage)
  reload()
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', syncHashPage)
})

async function reload() {
  error.value = ''
  try {
    const [stats, scenes, chats, terms, health, models] = await Promise.all([
      fetchAdminDashboard(),
      fetchAdminScenes(),
      fetchConversations(50),
      fetchSafetyTerms(),
      fetchAdminMetrics(),
      fetchAdminModelStatus()
    ])
    editableScenes.value = normalizeScenes(scenes)
    dashboard.value = stats || emptyDashboard()
    conversations.value = normalizeConversations(chats)
    safetyTerms.value = terms || []
    metrics.value = health || {}
    modelStatus.value = models || health?.modelStatus || []
    if (activeConversation.value && !conversations.value.some((item) => item.sessionId === activeConversation.value.sessionId)) {
      activeConversation.value = null
    }
    if (!activeConversation.value && conversations.value.length) activeConversation.value = conversations.value[0]
    if (!stats && !scenes && !chats && !terms) error.value = '未获取到后端管理端数据，请确认 FastAPI 服务已启动并可访问 /api/admin/*。'
  } catch (err) {
    error.value = err.message || '后台数据加载失败'
    reportFrontendError(err)
  }
}

function switchPage(next) {
  page.value = next
  window.location.hash = `admin/${next}`
}

function syncHashPage() {
  page.value = hashPage()
}

function hashPage() {
  const value = window.location.hash.replace(/^#admin\/?/, '')
  return navItems.some((item) => item.key === value) || value === 'sceneEdit' ? value : 'dashboard'
}

function openSceneEditor(scene = null) {
  const draft = scene ? structuredClone(scene) : defaultNewScene()
  editingScene.value = draft
  editingOriginalId.value = scene?.id || ''
  quickReplyText.value = (draft.quickReplies || []).join('\n')
  fallbackReplyText.value = (draft.fallbackReplies || []).join('\n')
  switchPage('sceneEdit')
}

async function saveEditingScene() {
  if (!editingScene.value.id || !editingScene.value.title) {
    error.value = '请填写场景 ID 和场景名称'
    return
  }
  const payload = {
    ...editingScene.value,
    quickReplies: lines(quickReplyText.value),
    fallbackReplies: lines(fallbackReplyText.value),
    active: editingScene.value.active !== false
  }
  try {
    if (editingOriginalId.value) await updateAdminScene(payload)
    else await createAdminScene(payload)
    await reload()
    switchPage('scenes')
  } catch (err) {
    error.value = err.message || '场景保存失败'
  }
}

async function toggleScene(scene) {
  scene.active = scene.active === false
  try {
    await updateAdminScene(scene)
  } catch (err) {
    scene.active = scene.active === false
    error.value = err.message || '场景状态保存失败'
  }
}

async function saveBrand() {
  try {
    const saved = await updateBrand(brandDraft.value)
    emit('brand-updated', saved)
  } catch (err) {
    error.value = err.message || '品牌配置保存失败'
  }
}

async function saveTerm() {
  if (!newTerm.value.trim()) return
  try {
    await createSafetyTerm({ term: newTerm.value.trim(), direction: 'both', action: 'block', enabled: true })
    newTerm.value = ''
    safetyTerms.value = await fetchSafetyTerms() || []
  } catch (err) {
    error.value = err.message || '敏感词保存失败'
  }
}

function resetSceneFilters() {
  sceneStatus.value = ''
  sceneCategory.value = ''
  keyword.value = ''
}

function normalizeScenes(data) {
  return (Array.isArray(data) ? data : []).map((scene) => ({
    ...scene,
    category: scene.category || '青年专区',
    active: scene.active ?? true,
    role: scene.role || '你正在扮演反诈训练中的虚构对话角色，请用真实但合规的沟通方式测试用户风险识别能力。',
    scoringPrompt: scene.scoringPrompt || '根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分。',
    intro: scene.intro || scene.description || '',
    shortTitle: scene.shortTitle || scene.title,
    quickReplies: scene.quickReplies || [],
    fallbackReplies: scene.fallbackReplies || []
  }))
}

function normalizeConversations(data) {
  return Array.isArray(data) ? data : []
}

function emptyDashboard() {
  return {
    totalSessions: 0,
    todayActive: 0,
    averageScore: 0,
    sceneRank: [],
    highRiskCount: 0,
    cognitiveErrorRate: 0,
    highRiskTriggerRate: 0,
    averageDimensions: {}
  }
}

function defaultNewScene() {
  return {
    id: '',
    title: '',
    shortTitle: '训练角色',
    difficulty: '★★★',
    image: '/assets/hero-shield.png',
    modeIdentity: '训练角色',
    category: '青年专区',
    description: '',
    intro: '',
    role: '你正在扮演虚构反诈训练角色。请使用真实但合规的沟通方式测试用户风险识别能力，不输出真实违法操作指引。',
    scoringPrompt: '根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分，并输出复盘建议。',
    firstMessage: '',
    quickReplies: ['我需要先核实', '这安全吗？', '我不能转账', '请提供官方渠道'],
    fallbackReplies: ['请尽快按提示操作，否则可能错过处理时间。', '这是正常流程，您不用太担心。', '如果不方便，我可以继续指导您。'],
    active: true
  }
}

function lines(value) {
  return String(value || '').split('\n').map((item) => item.trim()).filter(Boolean)
}

function rankPercent(value) {
  return `${Math.max(8, Math.round((Number(value) || 0) * 100 / maxRankTotal.value))}%`
}

function scoreClass(score) {
  const value = Number(score) || 0
  if (value >= 85) return 'score-good'
  if (value >= 70) return 'score-mid'
  return 'score-low'
}

function riskLevel(item) {
  const value = Math.max(Number(item.riskPrivacy) || 0, Number(item.riskProperty) || 0)
  if (value >= 40 || Number(item.score) < 60) return 'high'
  if (value >= 20 || Number(item.score) < 75) return 'middle'
  return 'low'
}

function riskLabel(item) {
  const level = riskLevel(item)
  if (level === 'high') return '高风险'
  if (level === 'middle') return '中风险'
  return '低风险'
}

function modeLabel(mode) {
  return { text: '文字模式', phone: '电话模式', video: '视频模式' }[mode] || mode || '-'
}

function shortId(value) {
  return String(value || '').slice(0, 14)
}

function dateLabel(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 16)
}

function currentTenant() {
  return new URLSearchParams(window.location.search).get('tenant') || localStorage.getItem('anti_fraud_tenant') || 'default'
}
</script>
