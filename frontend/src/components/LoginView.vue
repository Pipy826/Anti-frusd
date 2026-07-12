<template>
  <section class="screen login-screen">

    <div class="login-hero">
      <div class="login-brand">
        <span class="login-brand-mark">闪</span>
        <strong>反诈话术陪练助手</strong>
      </div>

      <div class="login-hero-content">
        <div class="login-copy">
          <h1>沉浸式对话演练<br>提升反诈实战能力</h1>
          <p>多种诈骗场景模拟 · AI对话陪练 · 智能评分复盘</p>
        </div>
        <div class="login-visual" aria-hidden="true">
          <span class="login-orbit"></span>
          <img src="/assets/hero-shield.png" alt="">
          <span class="login-chat-dot">•••</span>
        </div>
      </div>
    </div>

    <section class="login-card">
      <header class="login-card-head">
        <h2>{{ isAdminMode ? '管理端登录' : (isRegisterMode ? '注册账号' : '欢迎登录') }}</h2>
        <p>反诈话术陪练助手</p>
        <span>{{ isAdminMode ? '请使用管理员账号登录运营后台' : '沉浸式模拟对话，练就反诈火眼金睛' }}</span>
      </header>

      <div v-if="!isAdminMode" class="login-tabs">
        <button :class="{ active: !isRegisterMode }" @click="isRegisterMode = false">账号登录</button>
        <button :class="{ active: isRegisterMode }" @click="isRegisterMode = true">注册新号</button>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label class="login-field">
          <span class="login-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span>
          <input v-model="account" type="text" :placeholder="isAdminMode ? '请输入管理员账号' : (isRegisterMode ? '请输入用户名（2-30字符）' : '请输入用户名')" autocomplete="username">
        </label>
        <label v-if="isRegisterMode && !isAdminMode" class="login-field">
          <span class="login-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span>
          <input v-model="nickname" type="text" placeholder="请输入昵称（可选）" autocomplete="nickname">
        </label>
        <label class="login-field">
          <span class="login-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></span>
          <input v-model="password" :type="showPassword ? 'text' : 'password'" :placeholder="isRegisterMode ? '请设置密码（4位以上）' : '请输入密码'" autocomplete="current-password">
          <button type="button" class="eye-btn" aria-label="切换密码可见性" @click="showPassword = !showPassword">
            <svg v-if="!showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </label>
        <label v-if="isRegisterMode && !isAdminMode" class="login-field">
          <span class="login-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></span>
          <input v-model="confirmPassword" type="password" placeholder="请确认密码" autocomplete="new-password">
        </label>

        <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>

        <button class="login-submit" type="submit" :disabled="loading">
          {{ loading ? '请稍候...' : (isAdminMode ? '管理端登录' : (isRegisterMode ? '注册' : '登录')) }}
        </button>
      </form>

      <p class="register-line" v-if="isAdminMode">
        <button type="button" @click="backToUser">← 返回用户登录</button>
      </p>
      <p class="register-line" v-else-if="!isRegisterMode">
        还没有账号？ <button type="button" @click="isRegisterMode = true">立即注册</button>
      </p>
      <p class="register-line" v-else>
        已有账号？ <button type="button" @click="isRegisterMode = false">返回登录</button>
      </p>

      <div v-if="!isAdminMode" class="admin-entry">
        <button type="button" class="admin-entry-btn" @click="handleAdminLogin">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68 1.65 1.65 0 0 0 9.09 3V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          管理端登录
        </button>
      </div>
    </section>

    <i class="home-indicator" aria-hidden="true"></i>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { apiLogin, apiRegister, isAdmin } from '../services/api'

const emit = defineEmits(['login', 'admin-login'])

const account = ref('')
const password = ref('')
const confirmPassword = ref('')
const nickname = ref('')
const showPassword = ref(false)
const isRegisterMode = ref(false)
const isAdminMode = ref(false)
const loading = ref(false)
const errorMsg = ref('')

function handleAdminLogin() {
  isAdminMode.value = true
  isRegisterMode.value = false
  account.value = ''
  password.value = ''
  errorMsg.value = ''
}

function backToUser() {
  isAdminMode.value = false
  account.value = ''
  password.value = ''
  errorMsg.value = ''
}

async function handleSubmit() {
  errorMsg.value = ''

  if (!account.value.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!password.value) {
    errorMsg.value = '请输入密码'
    return
  }

  if (isRegisterMode.value) {
    if (account.value.trim().length < 2) {
      errorMsg.value = '用户名至少 2 个字符'
      return
    }
    if (password.value.length < 4) {
      errorMsg.value = '密码至少 4 位'
      return
    }
    if (password.value !== confirmPassword.value) {
      errorMsg.value = '两次密码不一致'
      return
    }
  }

  loading.value = true
  try {
    if (isRegisterMode.value) {
      await apiRegister(account.value.trim(), password.value, nickname.value.trim())
      emit('login')
    } else {
      await apiLogin(account.value.trim(), password.value)
      if (isAdminMode.value) {
        if (!isAdmin()) {
          errorMsg.value = '该账号没有管理员权限'
          return
        }
        emit('admin-login')
      } else {
        emit('login')
      }
    }
  } catch (err) {
    errorMsg.value = err.message || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-error {
  color: #ff5757;
  font-size: 13px;
  margin: -4px 0 8px;
  text-align: center;
}
.admin-entry {
  margin-top: 16px;
  text-align: center;
}
.admin-entry-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 20px;
  padding: 8px 20px;
  font-size: 13px;
  color: #8a9bbd;
  cursor: pointer;
  transition: all 0.2s;
}
.admin-entry-btn:hover {
  border-color: #4a7dff;
  color: #4a7dff;
}
.admin-entry-btn svg {
  display: block;
}
</style>
