import { getScene, scenes } from '../data/scenes'
import { loadHistory as loadLocalHistory } from '../utils/storage'

const API_TIMEOUT = 8000
const USE_API = import.meta.env.VITE_USE_API === 'true'

// ─── Token 管理 ──────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('anti_fraud_token') || ''
}

function setToken(token) {
  localStorage.setItem('anti_fraud_token', token)
}

function clearToken() {
  localStorage.removeItem('anti_fraud_token')
  localStorage.removeItem('anti_fraud_user')
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('anti_fraud_user') || 'null')
  } catch {
    return null
  }
}

function setStoredUser(user) {
  localStorage.setItem('anti_fraud_user', JSON.stringify(user))
}

export function isLoggedIn() {
  return Boolean(getToken())
}

export function isAdmin() {
  const user = getStoredUser()
  return user?.role === 'admin'
}

export function getCurrentUser() {
  return getStoredUser()
}

export function logout() {
  clearToken()
}

// ─── Auth API ────────────────────────────────────────────────────

export async function apiLogin(username, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || '登录失败')
  }
  const data = await response.json()
  setToken(data.token)
  setStoredUser(data.user)
  return data
}

export async function apiRegister(username, password, nickname) {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, nickname: nickname || username })
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || '注册失败')
  }
  const data = await response.json()
  setToken(data.token)
  setStoredUser(data.user)
  return data
}

export async function fetchCurrentUser() {
  const token = getToken()
  if (!token) return null
  try {
    const response = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      if (response.status === 401) clearToken()
      return null
    }
    const user = await response.json()
    setStoredUser(user)
    return user
  } catch {
    return null
  }
}

// ─── Request helpers ─────────────────────────────────────────────

function withTimeout(promise, timeout = API_TIMEOUT) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  return {
    signal: controller.signal,
    run: promise(controller.signal).finally(() => window.clearTimeout(timer))
  }
}

async function postJson(path, body, timeout = API_TIMEOUT) {
  if (!USE_API) throw new Error('本地模式未启用后端 API')
  const request = (signal) =>
    fetch(path, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(body),
      signal
    })
  const { run } = withTimeout(request, timeout)
  const response = await run
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || '网络稍差，请重试')
  }
  return response.json()
}

function xhrJson(path) {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest()
    xhr.open('GET', path, true)
    xhr.setRequestHeader('X-Tenant-ID', currentTenant())
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.timeout = API_TIMEOUT
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)) }
        catch { resolve(null) }
      } else {
        resolve(null)
      }
    }
    xhr.onerror = () => resolve(null)
    xhr.ontimeout = () => resolve(null)
    xhr.send()
  })
}

async function getJson(path) {
  if (!USE_API) return null
  return xhrJson(path)
}

async function getAdminJson(path) {
  return xhrJson(path)
}

async function postAdminJson(path, body, method = 'POST') {
  const request = (signal) =>
    fetch(path, {
      method,
      headers: jsonHeaders(),
      body: JSON.stringify(body),
      signal
    })
  const { run } = withTimeout(request)
  const response = await run
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || '后台接口请求失败')
  }
  return response.json()
}

export async function fetchScenes() {
  const data = await getJson('/api/scenes')
  return data || scenes
}

export async function fetchHistory(limit = 10) {
  const data = await getJson(`/api/history?limit=${limit}`)
  return data || loadLocalHistory()
}

export async function fetchBrand() {
  return getJson('/api/brand')
}

export async function fetchVoiceConfig(sceneId) {
  const data = await getJson(`/api/voice/config/${sceneId}`)
  return data || {}
}

export async function synthesizeSpeech(sceneId, text) {
  return postJson('/api/voice/tts', { scene_id: sceneId, text }, 18000)
}

export async function transcribeAudio(sceneId, audioBase64, mimeType = 'audio/L16;rate=16000') {
  return postJson('/api/voice/asr', { scene_id: sceneId, audioBase64, mimeType }, 24000)
}

export async function reportFrontendError(error, sessionId = '') {
  if (!USE_API) return
  try {
    const request = (signal) =>
      fetch('/api/frontend/error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: error?.message || String(error),
          stack: error?.stack || '',
          session_id: sessionId
        }),
        signal
      })
    const { run } = withTimeout(request)
    await run
  } catch {
    // Error reporting must never interrupt the user flow.
  }
}

export async function fetchAdminDashboard() {
  return getAdminJson('/api/admin/dashboard')
}

export async function fetchAdminMetrics() {
  return getAdminJson('/api/admin/metrics')
}

export async function fetchAdminModelStatus() {
  return getAdminJson('/api/admin/model-status')
}

export async function fetchAdminScenes() {
  return getAdminJson('/api/admin/scenes')
}

export async function updateAdminScene(scene) {
  return postAdminJson(`/api/admin/scenes/${scene.id}`, scene, 'PUT')
}

export async function createAdminScene(scene) {
  return postAdminJson('/api/admin/scenes', scene)
}

export async function updateBrand(brand) {
  return postAdminJson('/api/admin/brand', brand, 'PUT')
}

export async function fetchConversations(limit = 20) {
  return getAdminJson(`/api/admin/conversations?limit=${limit}`)
}

export async function fetchAdminUsers() {
  return getAdminJson('/api/admin/users')
}

export async function fetchSafetyTerms() {
  return getAdminJson('/api/admin/safety-terms')
}

export async function createSafetyTerm(term) {
  return postAdminJson('/api/admin/safety-terms', term)
}

export async function fetchUserSettings() {
  return getJson('/api/user/settings')
}

export async function updateUserSettings(settings) {
  return postAdminJson('/api/user/settings', settings, 'PUT')
}

export async function fetchUserStats() {
  return getJson('/api/user/stats')
}

async function postLikeJson(path, body, method = 'POST') {
  const request = (signal) =>
    fetch(path, {
      method,
      headers: jsonHeaders(),
      body: JSON.stringify(body),
      signal
    })
  const { run } = withTimeout(request)
  const response = await run
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || '网络稍差，请重试')
  }
  return response.json()
}

function currentTenant() {
  const params = new URLSearchParams(window.location.search)
  const tenant = params.get('tenant') || localStorage.getItem('anti_fraud_tenant') || 'default'
  localStorage.setItem('anti_fraud_tenant', tenant)
  return tenant
}

function tenantHeaders() {
  return { 'X-Tenant-ID': currentTenant() }
}

function authHeaders() {
  const token = getToken()
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

function jsonHeaders() {
  return { 'Content-Type': 'application/json', ...tenantHeaders(), ...authHeaders() }
}

export async function startChat(sceneId, mode) {
  try {
    const precheckAttemptId = sessionStorage.getItem(`precheck_${sceneId}`) || ''
    return await postJson('/api/chat/start', { scene_id: sceneId, mode, precheck_attempt_id: precheckAttemptId })
  } catch {
    const scene = getScene(sceneId)
    return {
      session_id: `local-${Date.now()}`,
      first_message: scene.firstMessage,
      degraded: true
    }
  }
}

export async function submitCognitive(sceneId, answers) {
  const result = await postJson('/api/cognitive/submit', {
    scene_id: sceneId,
    answers: answers.map((item) => ({ question_id: item.questionId, answer: item.answer }))
  })
  sessionStorage.setItem(`precheck_${sceneId}`, result.attempt_id)
  return result
}

export async function sendMessage(sessionId, sceneId, userMessage, round) {
  if (sessionId?.startsWith('local-')) {
    return localReply(sceneId, round, userMessage, sessionId)
  }
  try {
    return await postJson('/api/chat/send', { session_id: sessionId, user_message: userMessage })
  } catch (error) {
    if (String(error.message).includes('会话已过期')) throw error
    return { ...localReply(sceneId, round, userMessage, sessionId), degraded: true }
  }
}

export async function endChat(sessionId, sceneId) {
  if (sessionId?.startsWith('local-')) {
    return getScene(sceneId).review
  }
  try {
    return await postJson('/api/chat/end', { session_id: sessionId })
  } catch {
    return getScene(sceneId).review
  }
}

function localReply(sceneId, round, userMessage = '', sessionId = '') {
  const scene = getScene(sceneId)
  const intent = classifyIntent(userMessage)
  const replies = realisticReplies(sceneId, scene)[intent] || scene.fallbackReplies
  const risk = localRisk(userMessage, scene, sessionId)
  return {
    ai_reply: replies[round % replies.length],
    risk,
    quick_replies: risk.privacy >= 35 || risk.property >= 35
      ? ['我需要先核实', '我不会提供验证码', '我不点击陌生链接', '我会拨打 96110 咨询']
      : scene.quickReplies
  }
}

function classifyIntent(text = '') {
  if (['核实', '确认', '官方', '原号码', '群里', '家属', '家人', '联系', '医院', '派出所', '邻居', '暗号', '打电话', '96110', '报警'].some((word) => text.includes(word))) return 'verify'
  if (['不转', '不点', '不登', '不会', '拒绝', '算了', '不用', '不要', '骗子'].some((word) => text.includes(word))) return 'refuse'
  if (['好的', '可以', '马上', '现在', '我转', '我登', '我点', '发给我', '怎么转', '去银行'].some((word) => text.includes(word))) return 'comply'
  return 'question'
}

function realisticReplies(sceneId, scene) {
  const packs = {
    classmate_link: {
      verify: [
        '群里人太多，班长让我先私下确认名单。我现在不方便接电话，你先点【链接】看下有没有你的照片。',
        '发群里怕别人乱改信息。你就登一下校友身份，进去看一眼，不用付钱。'
      ],
      comply: [
        '对，就是这个【链接】。进去选微信/QQ 授权就行，页面如果弹验证码只是确认本人。',
        '你登进去后把页面停在相册页，我帮你看哪几张需要删。别退出，今晚要交名单。'
      ],
      refuse: [
        '你也太谨慎了吧，我刚才都登过。那你先别填验证码，只看相册页面总可以吧？',
        '行，那你晚点回我。只是截止后照片就默认保留了，到时别怪我没提醒。'
      ],
      question: [
        '因为里面有同学联系方式和老照片，平台要确认是本班的人。你进去只要授权，不涉及付款。',
        '班长找的校友平台，我也只是帮忙转。你先看页面，不放心就别填太多。'
      ]
    },
    hacked_friend_accident: {
      verify: [
        '别打电话，我这边真的接不了，旁边太乱了。你先联系我家里他们会急坏，先帮我垫一点急诊费。',
        '医院全称我等会发你，我现在手抖打字慢。你先看【事故照片】，这事不是开玩笑。'
      ],
      comply: [
        '谢谢，先垫急诊费就行。我把【收款信息】发你，等处理完我立刻还。',
        '你先转一点应急，医生这边一直催。别打语音，我现在真的说不清。'
      ],
      refuse: [
        '算了，我再想办法。只是现在真挺难的，你如果不放心，先帮我联系一个能马上到的人。',
        '你不转也行，先别在群里说，事情没弄清楚前我怕家里乱。'
      ],
      question: [
        '刚才太突然了，我也懵。车和人都在处理，先要交急诊费，别的问题我晚点跟你解释。',
        '不是借很多，就是先过这个窗口。你看【事故照片】就知道我没时间慢慢讲。'
      ]
    },
    elder_deepfake: {
      verify: [
        '妈，我手机快没电，原号码现在打不通。你先别找邻居，我怕事情传出去，你先帮我过这一关。',
        '暗号我一急想不起来，你先看【视频画面】，我人就在这。保证金交完我马上给你回电话。'
      ],
      comply: [
        '你先别挂视频。我把【收款信息】给你看，你到窗口前先按我说的确认一遍。',
        '妈别慌，按我说的来。不要告诉别人，免得他们担心，交完保证金我就能处理了。'
      ],
      refuse: [
        '那你先别转，先找舅舅确认也行。记住不要按视频里的人要求共享屏幕或说验证码。',
        '如果你不确定，就先挂断回拨我原来的号码。别急着去银行。'
      ],
      question: [
        '就是临时保证金，不是罚款。我这边人很多，没法细说，你看着我就知道是我。',
        '妈，手续后面都能补，现在卡在窗口。你先别问太多，我真怕来不及。'
      ]
    },
    family: {
      verify: [
        '他本人现在说话不方便，手机也摔坏了。我可以发一段【语音】，你听一下声音，先别耽误检查。',
        '家属那边还没联系上，老师只能先找你。你先垫一下，后面发票和手续都会补。'
      ],
      comply: [
        '那太好了，先垫检查费就行。我把【收款信息】发你，你先别退出聊天，我这边等窗口确认。',
        '你先别挂，我一步步跟你说。现在先处理付款，身份材料后面补。'
      ],
      refuse: [
        '理解，你谨慎是对的。那你先用原号码或家属确认，确认前不要转任何钱。',
        '如果你担心被骗，就先挂断核实。别通过我给的方式转账。'
      ],
      question: [
        '具体摔伤情况医生没让我多说，怕刺激家属。现在主要是检查费没法先挂账。',
        '不是借钱，是临时垫付。老师这边也在处理，只是窗口要先交费。'
      ]
    }
  }
  return packs[sceneId] || {
    verify: [
      '你先别到处问，这个流程有时间限制。我只能在当前通道帮你处理，晚了可能要重新排队。',
      '官方那边现在也会让你走同样流程。你先按这个页面提示做，后面有记录可查。'
    ],
    comply: [
      '对，先按提示操作。中途如果收到验证码或确认弹窗，不要退出，我会在这边同步看状态。',
      '好，你先保持在线。现在最关键是别中断，系统超时后会重新审核。'
    ],
    refuse: [
      '你不放心可以先暂停，自己通过官方渠道核实。确认前不要转账、不要给验证码。',
      '行，那先别操作。你可以拨打官方电话或 96110 问清楚。'
    ],
    question: scene.fallbackReplies
  }
}

function localRisk(text = '', scene, sessionId) {
  let privacyDelta = 0
  let propertyDelta = 0
  const reasons = []
  const privacyWords = scene.riskTriggers?.privacy || ['验证码', '身份证', '银行卡', '密码', '账号', '人脸', '视频', '语音']
  const propertyWords = scene.riskTriggers?.property || ['转账', '付款', '充值', '链接', '保证金', '医药费', '急诊费']
  privacyWords.forEach((word) => {
    if (word && text.includes(word)) {
      privacyDelta += 8
      reasons.push(`提到敏感信息：${word}`)
    }
  })
  propertyWords.forEach((word) => {
    if (word && text.includes(word)) {
      propertyDelta += 10
      reasons.push(`提到资金动作：${word}`)
    }
  })
  if (['好的', '可以', '马上', '我转', '我登', '我点', '去银行', '发给我'].some((word) => text.includes(word))) {
    propertyDelta += 10
    reasons.push('存在顺从高压话术倾向')
  }
  if (['核实', '官方', '原号码', '家属', '家人', '联系', '报警', '96110', '不转账', '不点击', '拒绝'].some((word) => text.includes(word))) {
    privacyDelta -= 8
    propertyDelta -= 10
    reasons.push('出现主动核验或拒绝行为')
  }
  privacyDelta = Math.max(-15, Math.min(45, privacyDelta))
  propertyDelta = Math.max(-15, Math.min(45, propertyDelta))
  const key = sessionId ? `local_risk_${sessionId}` : ''
  const previous = key ? JSON.parse(sessionStorage.getItem(key) || '{"privacy":0,"property":0}') : { privacy: 0, property: 0 }
  const privacy = Math.max(0, Math.min(100, previous.privacy + privacyDelta))
  const property = Math.max(0, Math.min(100, previous.property + propertyDelta))
  if (key) sessionStorage.setItem(key, JSON.stringify({ privacy, property }))
  return {
    privacy,
    property,
    privacy_delta: privacyDelta,
    property_delta: propertyDelta,
    reason: reasons.length ? [...new Set(reasons)].join('；') : '未发现明显高危信息',
    warning: privacyDelta >= 20 || propertyDelta >= 20 ? '这句话可能暴露隐私或造成资金风险，建议先暂停并通过官方渠道核实。' : ''
  }
}
