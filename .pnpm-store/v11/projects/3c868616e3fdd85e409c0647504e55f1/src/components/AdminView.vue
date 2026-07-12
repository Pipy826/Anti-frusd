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
          <span class="nav-svg" v-html="item.icon"></span>{{ item.label }}
          <i v-if="item.badge" class="nav-badge">{{ item.badge }}</i>
        </button>
      </nav>

      <div class="admin-sidebar-footer">
        <a :href="exportHref" download><span class="footer-icon">📊</span> 导出报表</a>
        <button class="sidebar-back-btn" @click="$emit('go', 'home')"><span class="footer-icon">←</span> 返回前台</button>
        <button class="sidebar-logout-btn" @click="handleLogout"><span class="footer-icon">⏻</span> 退出登录</button>
        <small>© 2024 反诈话术陪练助手<br>v2.0.0</small>
      </div>
    </aside>

    <main class="admin-main">
      <header class="admin-topbar">
        <button class="admin-menu-btn" title="菜单">☰</button>
        <div class="topbar-title">
          <h1>{{ currentNav.label }}</h1>
          <p>{{ currentNav.desc }}</p>
        </div>
        <div class="admin-top-actions">
          <label class="admin-search">
            <input v-model="keyword" :placeholder="currentNav.search || '搜索场景/用户/关键词...'" />
            <span>🔍</span>
          </label>
          <button class="admin-notify-btn" title="通知">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            <i v-if="notifyCount > 0" class="notify-badge">{{ notifyCount }}</i>
          </button>
          <div class="admin-user-dropdown">
            <img :src="adminUser?.avatar || '/assets/profile-avatar.png'" alt="">
            <span>{{ adminUser?.nickname || '管理员' }}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
        </div>
      </header>

      <p v-if="error" class="admin-error">{{ error }}</p>

      <section v-if="page === 'dashboard'" class="admin-content">
        <div class="admin-stat-grid">
          <article v-for="metric in dashboardMetrics" :key="metric.label" :class="['admin-stat-card', metric.color]">
            <div class="stat-icon-wrap">
              <span class="stat-icon" v-html="metric.icon"></span>
            </div>
            <div class="stat-body">
              <span>{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <small v-if="metric.trend !== 0" :class="metric.trend > 0 ? 'trend-up' : 'trend-down'">较昨日 {{ metric.trend > 0 ? '↑' : '↓' }} {{ Math.abs(metric.trend) }}{{ metric.trendUnit }}</small>
              <small v-else class="trend-neutral">较昨日持平</small>
            </div>
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
                <button class="seg-calendar" title="选择日期">📅</button>
              </div>
            </div>
            <div class="chart-legend">
              <span class="legend-item legend-sessions"><i></i> 体验人次</span>
              <span class="legend-item legend-active"><i></i> 活跃人数</span>
            </div>
            <div class="admin-line-chart">
              <div class="chart-y-axis">
                <span>1,500</span><span>1,200</span><span>900</span><span>600</span><span>300</span><span>0</span>
              </div>
              <div class="chart-area">
                <svg v-if="trendSessions.length" class="chart-svg" viewBox="0 0 600 260" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="fillSessions" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="rgba(18,108,255,.18)" />
                      <stop offset="100%" stop-color="rgba(18,108,255,0)" />
                    </linearGradient>
                    <linearGradient id="fillActive" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="rgba(33,197,154,.15)" />
                      <stop offset="100%" stop-color="rgba(33,197,154,0)" />
                    </linearGradient>
                  </defs>
                  <path :d="sessionAreaPath" fill="url(#fillSessions)" />
                  <path :d="sessionLinePath" fill="none" stroke="#126cff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                  <path :d="activeAreaPath" fill="url(#fillActive)" />
                  <path :d="activeLinePath" fill="none" stroke="#21c59a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                  <circle v-for="(pt, idx) in sessionPoints" :key="'s'+idx" :cx="pt.x" :cy="pt.y" r="4" fill="#126cff" />
                  <circle v-for="(pt, idx) in activePoints" :key="'a'+idx" :cx="pt.x" :cy="pt.y" r="4" fill="#21c59a" />
                </svg>
                <p v-else class="admin-empty">暂无真实趋势数据</p>
              </div>
              <div class="chart-x-axis">
                <span v-for="label in trendXLabels" :key="label">{{ label }}</span>
              </div>
            </div>
          </section>

          <section class="admin-card">
            <div class="admin-card-head">
              <h2>热门场景 TOP5</h2>
              <button @click="switchPage('scenes')">更多 ›</button>
            </div>
            <div class="admin-rank-list">
              <p v-if="!sceneRank.length" class="admin-empty">暂无真实排行数据</p>
              <p v-for="(item, index) in sceneRank.slice(0, 5)" :key="item.title" class="rank-row">
                <b :class="'rank-' + (index + 1)">{{ index + 1 }}</b>
                <img :src="item.image || sceneIcon(index)" class="rank-scene-icon" alt="">
                <span class="rank-title">{{ item.title }}</span>
                <strong class="rank-count">{{ formatNumber(item.total) }}</strong>
                <em class="rank-percent">{{ rankPercentNum(item.total) }}%</em>
              </p>
            </div>
          </section>

          <section class="admin-card admin-wide">
            <div class="admin-card-head">
              <h2>最新对话记录</h2>
              <button @click="switchPage('conversations')">更多 ›</button>
            </div>
            <table class="admin-table">
              <thead>
                <tr><th></th><th>用户ID</th><th>场景</th><th>模式</th><th>得分</th><th>时长</th><th>结束时间</th><th>操作</th></tr>
              </thead>
              <tbody>
                <tr v-if="!conversations.length">
                  <td colspan="8" class="admin-empty-cell">暂无真实对话记录</td>
                </tr>
                <tr v-for="(item, idx) in conversations.slice(0, 5)" :key="item.sessionId">
                  <td><img :src="userAvatar(idx)" class="table-avatar" alt=""></td>
                  <td class="user-id-cell">{{ item.userName || '匿名用户' }}</td>
                  <td>{{ item.sceneTitle }}</td>
                  <td><span class="mode-tag">{{ modeLabel(item.mode) }}</span></td>
                  <td><b :class="scoreClass(item.score)">{{ item.score || '-' }}</b></td>
                  <td>{{ durationLabel(item.duration) }}</td>
                  <td>{{ dateLabel(item.createdAt) }}</td>
                  <td><button class="view-btn" @click="activeConversation = item; switchPage('conversations')">查看</button></td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="admin-card">
            <div class="admin-card-head">
              <h2>风险预警</h2>
              <button @click="switchPage('audit')">更多 ›</button>
            </div>
            <div class="admin-alert-list-v2">
              <div v-for="alert in riskAlerts" :key="alert.title" class="alert-item">
                <span :class="['alert-badge', alert.level]">{{ alert.badge }}</span>
                <div class="alert-body">
                  <b>{{ alert.title }}</b>
                  <small>{{ alert.desc }}</small>
                </div>
                <time>{{ alert.time }}</time>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section v-if="page === 'scenes'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card stat-blue">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg></span></div>
            <div class="stat-body"><span>全部场景</span><strong>{{ editableScenes.length }}</strong><small class="trend-neutral">训练内容库</small></div>
          </article>
          <article class="admin-stat-card stat-green">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></span></div>
            <div class="stat-body"><span>已上线</span><strong>{{ activeSceneCount }}</strong><small class="trend-neutral">前台可见</small></div>
          </article>
          <article class="admin-stat-card stat-orange">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></span></div>
            <div class="stat-body"><span>未上线</span><strong>{{ editableScenes.length - activeSceneCount }}</strong><small class="trend-neutral">草稿或停用</small></div>
          </article>
          <article class="admin-stat-card stat-purple">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg></span></div>
            <div class="stat-body"><span>场景标签</span><strong>{{ sceneCategories.length }}</strong><small class="trend-neutral">分类覆盖</small></div>
          </article>
        </div>

        <section class="admin-card">
          <div class="admin-card-head">
            <h2>场景管理</h2>
            <button class="admin-primary-btn" @click="openSceneEditor()">+ 新增场景</button>
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
                <td colspan="6" class="admin-empty-cell">暂无场景数据</td>
              </tr>
              <tr v-for="scene in filteredScenes" :key="scene.id" class="scene-row">
                <td>
                  <div class="scene-cell">
                    <img :src="scene.image || '/assets/hero-shield.png'" alt="">
                    <div><b>{{ scene.title }}</b><small>{{ scene.description }}</small></div>
                  </div>
                </td>
                <td><span class="admin-tag">{{ scene.category || '未分类' }}</span></td>
                <td><span class="difficulty-stars">{{ scene.difficulty }}</span></td>
                <td>
                  <button :class="['switch-btn', { on: scene.active !== false }]" @click="toggleScene(scene)">
                    {{ scene.active === false ? '未上线' : '已上线' }}
                  </button>
                </td>
                <td><span class="version-tag">v{{ scene.promptVersion || 1 }}</span></td>
                <td>
                  <button class="edit-btn" @click="openSceneEditor(scene)">编辑</button>
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
            <label>角色身份<input v-model="editingScene.modeIdentity" placeholder="如：快递客服"></label>
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
        <aside class="conversation-filter">
          <div class="filter-header">
            <h2>筛选条件</h2>
          </div>
          <div class="filter-form">
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
            <button class="filter-search-btn" @click="reload">查询</button>
            <a class="filter-export-link" :href="exportHref" download>导出数据</a>
          </div>
        </aside>

        <section class="conversation-list">
          <div class="conv-list-header">
            <h2>共 <b>{{ filteredConversations.length }}</b> 条记录</h2>
          </div>
          <div class="conv-list-scroll">
            <p v-if="!filteredConversations.length" class="admin-empty">暂无对话记录</p>
            <button
              v-for="item in filteredConversations"
              :key="item.sessionId"
              :class="['conv-item', { active: activeConversation?.sessionId === item.sessionId }]"
              @click="activeConversation = item"
            >
              <div class="conv-item-main">
                <b>{{ item.sceneTitle }}</b>
                <small>{{ item.userName || '匿名用户' }} · {{ modeLabel(item.mode) }}</small>
                <span :class="['conv-risk-label', riskLevel(item)]">{{ riskLabel(item) }}</span>
              </div>
              <div class="conv-item-score" :class="scoreClass(item.score)">
                <em>{{ item.score || '-' }}</em>分
              </div>
            </button>
          </div>
        </section>

        <section class="conversation-detail">
          <div class="detail-header">
            <h2>对话详情</h2>
            <a :href="exportHref" download>导出对话</a>
          </div>
          <div v-if="activeConversation" class="conversation-summary">
            <div class="summary-item">
              <span>会话ID</span>
              <b>{{ shortId(activeConversation.sessionId) }}</b>
            </div>
            <div class="summary-item">
              <span>场景</span>
              <b>{{ activeConversation.sceneTitle }}</b>
            </div>
            <div class="summary-item">
              <span>模式</span>
              <b>{{ modeLabel(activeConversation.mode) }}</b>
            </div>
            <div class="summary-item">
              <span>风险</span>
              <b>{{ activeConversation.riskPrivacy }} / {{ activeConversation.riskProperty }}</b>
            </div>
          </div>
          <div class="message-timeline">
            <p v-if="!activeConversationMessages.length" class="admin-empty">请选择一条对话记录查看详情</p>
            <article v-for="(message, index) in activeConversationMessages" :key="`${message.role}-${index}`" :class="['msg-bubble', message.role]">
              <div class="msg-avatar">
                <span>{{ message.role === 'user' ? '用户' : 'AI' }}</span>
              </div>
              <div class="msg-content">
                <p>{{ message.text }}</p>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-if="page === 'users'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card stat-blue"><div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg></span></div><div class="stat-body"><span>总用户数</span><strong>{{ registeredUsers.length }}</strong><small>平台注册用户</small></div></article>
          <article class="admin-stat-card stat-green"><div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></span></div><div class="stat-body"><span>今日活跃</span><strong>{{ registeredUsers.filter(u => u.todayActive).length }}</strong><small>今日登录用户</small></div></article>
          <article class="admin-stat-card stat-orange"><div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></span></div><div class="stat-body"><span>平均训练次数</span><strong>{{ Math.round(registeredUsers.reduce((a, u) => a + (u.totalSessions || 0), 0) / Math.max(1, registeredUsers.length)) }}</strong><small>人均完成场景数</small></div></article>
          <article class="admin-stat-card stat-purple"><div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span></div><div class="stat-body"><span>管理员</span><strong>{{ registeredUsers.filter(u => u.role === 'admin').length }}</strong><small>拥有管理权限</small></div></article>
        </div>
        <section class="admin-card">
          <div class="admin-card-head">
            <h2>用户列表</h2>
          </div>
          <table class="admin-table">
            <thead>
              <tr><th></th><th>昵称</th><th>用户名</th><th>角色</th><th>训练次数</th><th>平均得分</th><th>最近活跃</th></tr>
            </thead>
            <tbody>
              <tr v-if="!registeredUsers.length">
                <td colspan="7" class="admin-empty-cell">暂无用户数据</td>
              </tr>
              <tr v-for="user in registeredUsers" :key="'u'+user.id">
                <td><img :src="user.avatar || '/assets/profile-avatar.png'" class="table-avatar" alt=""></td>
                <td>{{ user.nickname }}</td>
                <td class="user-id-cell">{{ user.username }}</td>
                <td><span :class="['role-chip', user.role === 'admin' ? 'role-admin' : 'role-user']">{{ user.role === 'admin' ? '管理员' : '用户' }}</span></td>
                <td>{{ user.totalSessions }}</td>
                <td><b :class="scoreClass(user.avgScore)">{{ user.avgScore || '-' }}</b></td>
                <td>{{ user.lastActive ? dateLabel(user.lastActive) : '未训练' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </section>

      <section v-if="page === 'audit'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card stat-blue">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span></div>
            <div class="stat-body"><span>敏感词规则</span><strong>{{ safetyTerms.length }}</strong><small class="trend-neutral">已启用规则</small></div>
          </article>
          <article class="admin-stat-card stat-orange">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span></div>
            <div class="stat-body"><span>待关注会话</span><strong>{{ highRiskConversations.length }}</strong><small class="trend-neutral">需要人工复核</small></div>
          </article>
          <article class="admin-stat-card stat-purple">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span></div>
            <div class="stat-body"><span>高风险触发率</span><strong>{{ dashboard.highRiskTriggerRate }}%</strong><small class="trend-neutral">全平台统计</small></div>
          </article>
          <article class="admin-stat-card stat-green">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></span></div>
            <div class="stat-body"><span>安全会话</span><strong>{{ conversations.length - highRiskConversations.length }}</strong><small class="trend-neutral">正常结束</small></div>
          </article>
        </div>

        <div class="audit-grid">
          <section class="audit-term-panel">
            <div class="audit-panel-head">
              <h2>敏感词库</h2>
              <span class="audit-count">{{ safetyTerms.length }} 条规则</span>
            </div>
            <div class="term-form">
              <input v-model="newTerm" placeholder="输入需要拦截或提示的词">
              <button class="term-add-btn" @click="saveTerm">添加</button>
            </div>
            <div class="term-list-scroll">
              <p v-if="!safetyTerms.length" class="admin-empty">暂无敏感词规则</p>
              <div v-for="term in safetyTerms" :key="term.id" class="term-item">
                <span class="term-word">{{ term.term }}</span>
                <span class="term-meta">
                  <em :class="'term-dir-' + term.direction">{{ term.direction === 'both' ? '双向' : term.direction === 'input' ? '输入' : '输出' }}</em>
                  <em :class="'term-act-' + term.action">{{ term.action === 'block' ? '拦截' : '提示' }}</em>
                </span>
              </div>
            </div>
          </section>

          <section class="audit-content-panel">
            <div class="audit-panel-head">
              <h2>待关注内容</h2>
              <span class="audit-count">{{ highRiskConversations.length }} 条记录</span>
            </div>
            <div class="audit-table-wrap">
              <table class="admin-table audit-table">
                <thead>
                  <tr><th>会话ID</th><th>场景</th><th>风险等级</th><th>摘要</th><th>操作</th></tr>
                </thead>
                <tbody>
                  <tr v-if="!highRiskConversations.length">
                    <td colspan="5" class="admin-empty-cell">暂无高风险内容</td>
                  </tr>
                  <tr v-for="item in highRiskConversations" :key="item.sessionId" class="audit-row">
                    <td class="audit-id">{{ shortId(item.sessionId) }}</td>
                    <td><span class="admin-tag">{{ item.sceneTitle }}</span></td>
                    <td><span :class="['risk-chip', riskLevel(item)]">{{ riskLabel(item) }}</span></td>
                    <td class="audit-summary">{{ item.messages?.[0]?.text || '暂无摘要' }}</td>
                    <td><button class="view-btn" @click="activeConversation = item; switchPage('conversations')">查看</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>

      <section v-if="page === 'stats'" class="admin-content">
        <div class="admin-stat-grid">
          <article class="admin-stat-card stat-blue">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></span></div>
            <div class="stat-body"><span>API 成功率</span><strong>{{ metrics.apiSuccessRate || 100 }}%</strong><small class="trend-neutral">近一小时</small></div>
          </article>
          <article class="admin-stat-card stat-green">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span></div>
            <div class="stat-body"><span>平均响应</span><strong>{{ metrics.averageResponseMs || 0 }}ms</strong><small class="trend-neutral">接口耗时</small></div>
          </article>
          <article class="admin-stat-card stat-orange">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span></div>
            <div class="stat-body"><span>模型失败</span><strong>{{ metrics.llmFailureCount || 0 }}</strong><small class="trend-neutral">降级次数</small></div>
          </article>
          <article class="admin-stat-card stat-purple">
            <div class="stat-icon-wrap"><span class="stat-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></span></div>
            <div class="stat-body"><span>活跃会话</span><strong>{{ metrics.activeSessions || 0 }}</strong><small class="trend-neutral">当前在线</small></div>
          </article>
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
        <div class="settings-layout">
          <section class="admin-card">
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
              <button class="admin-secondary-btn" @click="brandDraft = { ...brand }">重置</button>
              <button class="admin-primary-btn" @click="saveBrand">保存配置</button>
            </div>
          </section>

          <div class="settings-side">
            <section class="admin-card">
              <div class="admin-card-head"><h2>模型状态</h2></div>
              <div class="model-status-list">
                <div v-for="model in modelStatus" :key="model.provider || model.name" class="model-status-item">
                  <div class="model-status-info">
                    <b>{{ model.provider || model.name }}</b>
                    <small>{{ model.model || 'LLM 模型' }}</small>
                  </div>
                  <span :class="['model-status-badge', { available: model.available !== false }]">
                    {{ model.available === false ? '不可用' : '运行中' }}
                  </span>
                </div>
                <div v-if="!modelStatus.length" class="model-status-item">
                  <div class="model-status-info"><b>暂无模型数据</b><small>请检查后端连接</small></div>
                </div>
              </div>
            </section>

            <section class="admin-card">
              <div class="admin-card-head"><h2>系统信息</h2></div>
              <div class="sys-info-list">
                <div class="sys-info-item"><span>系统版本</span><b>v2.0.0</b></div>
                <div class="sys-info-item"><span>运行环境</span><b>Production</b></div>
                <div class="sys-info-item"><span>敏感词规则</span><b>{{ safetyTerms.length }} 条</b></div>
                <div class="sys-info-item"><span>场景总数</span><b>{{ editableScenes.length }} 个</b></div>
              </div>
            </section>
          </div>
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
  fetchAdminUsers,
  fetchSafetyTerms,
  reportFrontendError,
  updateAdminScene,
  updateBrand,
  getCurrentUser,
  logout
} from '../services/api'

const props = defineProps({
  brand: { type: Object, required: true }
})
const emit = defineEmits(['go', 'brand-updated', 'logout'])

const adminUser = ref(getCurrentUser())

function handleLogout() {
  logout()
  emit('logout')
}

const navItems = [
  { key: 'dashboard', label: '数据看板', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>', desc: '您好，管理员！欢迎回来', search: '搜索指标/场景...' },
  { key: 'scenes', label: '场景管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>', desc: '管理训练场景内容，支持新增、编辑与上下线', search: '搜索场景名称/标签...' },
  { key: 'conversations', label: '对话管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', desc: '查看用户对话详情，支持内容检索与导出', search: '搜索用户ID/场景/关键词...' },
  { key: 'users', label: '用户管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>', desc: '管理平台用户信息与权限', search: '搜索用户ID/名称...' },
  { key: 'audit', label: '内容审核', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>', desc: '处理高风险对话内容，维护敏感词库', search: '搜索违规摘要/敏感词...' },
  { key: 'stats', label: '数据统计', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>', desc: '查看接口、模型与训练效果的细粒度统计', search: '搜索统计项...' },
  { key: 'settings', label: '系统设置', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68 1.65 1.65 0 0 0 9.09 3V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>', desc: '配置品牌展示、模型状态与安全策略', search: '搜索配置项...' }
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
const registeredUsers = ref([])
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
const dashboardMetrics = computed(() => {
  const d = dashboard.value
  const totalTrend = d.yesterdayTotal ? round2((d.totalSessions - d.yesterdayTotal) * 100 / d.yesterdayTotal) : 0
  const activeTrend = d.yesterdayActive ? round2((d.todayActive - d.yesterdayActive) * 100 / d.yesterdayActive) : 0
  const scoreTrend = d.yesterdayAverageScore ? round2(d.averageScore - d.yesterdayAverageScore) : 0
  const riskTrend = d.yesterdayHighRiskRate !== undefined ? round2(d.highRiskTriggerRate - d.yesterdayHighRiskRate) : 0
  return [
    { label: '累计体验人次', value: formatNumber(d.totalSessions), color: 'stat-blue', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>', trend: totalTrend, trendUnit: '%' },
    { label: '今日活跃人数', value: formatNumber(d.todayActive), color: 'stat-green', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>', trend: activeTrend, trendUnit: '%' },
    { label: '平均反诈得分', value: `${d.averageScore} 分`, color: 'stat-orange', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>', trend: scoreTrend, trendUnit: '分' },
    { label: '高危行为触发率', value: `${d.highRiskTriggerRate}%`, color: 'stat-purple', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>', trend: riskTrend, trendUnit: '%' }
  ]
})
const trendBucketCount = computed(() => range.value === 'today' ? 12 : range.value === '7d' ? 7 : 30)
const trendXLabels = computed(() => {
  if (range.value === 'today') return ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
  if (range.value === '7d') return ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  return Array.from({ length: 6 }, (_, i) => `${i * 5 + 1}日`)
})
const trendSessions = computed(() => {
  const bucketCount = trendBucketCount.value
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
  return buckets
})
const trendActive = computed(() => {
  // Derive active users from conversations - count unique session IDs per bucket
  const bucketCount = trendBucketCount.value
  const now = Date.now()
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const start = range.value === 'today' ? todayStart.getTime() : now - bucketCount * 24 * 60 * 60 * 1000
  const span = Math.max(1, now - start)
  const buckets = Array.from({ length: bucketCount }, () => new Set())

  conversations.value.forEach((item) => {
    const time = Date.parse(item.createdAt || '')
    if (!Number.isFinite(time) || time < start || time > now) return
    const index = Math.min(bucketCount - 1, Math.floor(((time - start) / span) * bucketCount))
    // Use sessionId as proxy for unique users
    buckets[index].add(item.sessionId)
  })
  return buckets.map(s => s.size)
})
const chartMax = computed(() => Math.max(10, ...trendSessions.value, ...trendActive.value))

function buildChartPoints(data) {
  const max = chartMax.value
  const count = data.length
  if (!count) return []
  return data.map((val, i) => ({
    x: count === 1 ? 300 : (i / (count - 1)) * 580 + 10,
    y: 250 - (val / max) * 230
  }))
}

const sessionPoints = computed(() => buildChartPoints(trendSessions.value))
const activePoints = computed(() => buildChartPoints(trendActive.value))
const sessionLinePath = computed(() => sessionPoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' '))
const activeLinePath = computed(() => activePoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' '))
const sessionAreaPath = computed(() => {
  if (!sessionPoints.value.length) return ''
  const pts = sessionPoints.value
  return `${sessionLinePath.value} L${pts[pts.length - 1].x},260 L${pts[0].x},260 Z`
})
const activeAreaPath = computed(() => {
  if (!activePoints.value.length) return ''
  const pts = activePoints.value
  return `${activeLinePath.value} L${pts[pts.length - 1].x},260 L${pts[0].x},260 Z`
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
const riskAlerts = computed(() => {
  const now = new Date()
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  return [
    { level: 'danger', badge: '高危', title: '高危行为触发率异常', desc: `${highRiskConversations.value.length} 条高风险会话，触发率 ${dashboard.value.highRiskTriggerRate}%`, time: timeStr },
    { level: 'warning', badge: '中危', title: 'API调用失败率', desc: `模型降级 ${metrics.value?.llmFailureCount || 0} 次，成功率 ${metrics.value?.apiSuccessRate || 100}%`, time: timeStr },
    { level: 'info', badge: '提示', title: '内容审核待处理', desc: `当前启用 ${safetyTerms.value.length} 条敏感词规则`, time: timeStr }
  ]
})

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
    const [stats, scenes, chats, terms, health, models, usersData] = await Promise.all([
      fetchAdminDashboard(),
      fetchAdminScenes(),
      fetchConversations(50),
      fetchSafetyTerms(),
      fetchAdminMetrics(),
      fetchAdminModelStatus(),
      fetchAdminUsers()
    ])
    editableScenes.value = normalizeScenes(scenes)
    dashboard.value = stats || emptyDashboard()
    conversations.value = normalizeConversations(chats)
    safetyTerms.value = terms || []
    metrics.value = health || {}
    modelStatus.value = models || health?.modelStatus || []
    registeredUsers.value = usersData || []
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
  const draft = scene ? JSON.parse(JSON.stringify(scene)) : defaultNewScene()
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
    modeIdentity: editingScene.value.modeIdentity || editingScene.value.modeIdentity || editingScene.value.title,
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
    active: Boolean(scene.active),
    modeIdentity: scene.modeIdentity || scene.title,
    role: scene.role || '你正在扮演反诈训练中的虚构对话角色，请用真实但合规的沟通方式测试用户风险识别能力。',
    scoringPrompt: scene.scoringPrompt || '根据对话记录从风险识别速度、信息保护程度、应对话术有效性、止损效率四个维度评分。',
    intro: scene.intro || scene.description || '',
    shortTitle: scene.shortTitle || scene.title,
    quickReplies: Array.isArray(scene.quickReplies) ? scene.quickReplies : [],
    fallbackReplies: Array.isArray(scene.fallbackReplies) ? scene.fallbackReplies : []
  }))
}

function normalizeConversations(data) {
  return Array.isArray(data) ? data : []
}

function emptyDashboard() {
  return {
    totalSessions: 0,
    todayActive: 0,
    yesterdayActive: 0,
    yesterdayTotal: 0,
    averageScore: 0,
    yesterdayAverageScore: 0,
    sceneRank: [],
    highRiskCount: 0,
    cognitiveErrorRate: 0,
    highRiskTriggerRate: 0,
    yesterdayHighRiskRate: 0,
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

function rankPercentNum(value) {
  const total = dashboard.value.totalSessions || 1
  return Math.round((Number(value) || 0) * 100 / total)
}

function formatNumber(num) {
  return Number(num || 0).toLocaleString()
}

function round2(val) {
  return Math.round(val * 10) / 10
}

function sceneIcon(index) {
  const icons = ['/assets/scene-delivery.png', '/assets/scene-family.png', '/assets/scene-job.png', '/assets/hero-shield.png', '/assets/hero-shield.png']
  return icons[index] || icons[0]
}

function userId(sessionId) {
  return 'U' + String(sessionId || '').replace(/[^0-9]/g, '').slice(0, 10).padEnd(10, '0')
}

function conversationCountFor(sessionId) {
  // Count how many conversations have the same user (approximated by IP/session prefix)
  const prefix = String(sessionId || '').slice(0, 8)
  return conversations.value.filter(c => String(c.sessionId || '').slice(0, 8) === prefix).length
}

function userAvatar(idx) {
  const colors = ['#126cff', '#21c59a', '#f59e0b', '#e8323b', '#8b5cf6']
  return `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="16" fill="${encodeURIComponent(colors[idx % colors.length])}"/><text x="16" y="21" text-anchor="middle" fill="white" font-size="14" font-family="sans-serif">${idx + 1}</text></svg>`
}

function durationLabel(duration) {
  if (!duration) return '-'
  const mins = Math.floor(duration / 60)
  const secs = duration % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

const notifyCount = computed(() => highRiskConversations.value.length)

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
