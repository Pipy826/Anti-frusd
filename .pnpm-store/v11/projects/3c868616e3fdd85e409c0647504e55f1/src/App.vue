<template>
  <main class="app" :class="{ 'app-admin': screen === 'admin' }" aria-live="polite">
    <HomeView
      v-if="screen === 'home'"
      :scenes="scenes"
      :brand="brand"
      @select-scene="openModeModal"
      @go="go"
    />

    <ChatView
      v-if="screen === 'chat'"
      :scene="currentScene"
      :messages="messages"
      :loading="chatLoading"
      :error="chatError"
      :risk="riskState"
      :quick-replies="quickReplies"
      :asr-supported="asrSupported"
      @back="go('home')"
      @send="handleSend"
      @end="finishChallenge"
      @speak="speak"
      @listen="startSpeechInput"
    />

    <CalibrationView
      v-if="screen === 'calibration'"
      :scene="pendingScene"
      @back="go('home')"
      @continue="startChallenge(pendingMode)"
    />

    <IncomingCallView
      v-if="screen === 'incoming'"
      :scene="currentScene"
      :voice="voiceSettings"
      @reject="go('home')"
      @accept="acceptCall"
    />

    <ActiveCallView
      v-if="screen === 'call'"
      :scene="currentScene"
      :timer="callTimerLabel"
      :state="callState"
      :loading="chatLoading"
      :error="chatError"
      :asr-supported="asrSupported"
      :messages="messages"
      @back="go('incoming')"
      @send="handleSend"
      @listen="startSpeechInput"
      @hangup="finishChallenge"
    />

    <VideoCallView
      v-if="screen === 'video'"
      :scene="currentScene"
      :timer="callTimerLabel"
      :loading="chatLoading"
      @send="handleSend"
      @hangup="finishChallenge"
    />

    <ReviewView
      v-if="screen === 'review'"
      :review="currentReview"
      :scene="currentScene"
      @retry="restartCurrent"
      @change-scene="go('home')"
      @detail="go('detail')"
    />

    <ReviewDetailView
      v-if="screen === 'detail'"
      :review="currentReview"
      :messages="messages"
      @back="go('review')"
    />

    <HistoryView
      v-if="screen === 'history'"
      :history="history"
      @open="openHistory"
      @go="go"
    />

    <ProfileView
      v-if="screen === 'profile'"
      @clear="clearLocalHistory"
      @go="go"
    />

    <AdminView
      v-if="screen === 'admin'"
      :brand="brand"
      @go="go"
      @brand-updated="handleBrandUpdated"
    />

    <GamifiedView
      v-if="screen === 'game'"
      :scenes="scenes"
      :history="history"
      @go="go"
    />

    <ModeModal
      v-if="modeModalVisible"
      :scene="pendingScene"
      @close="modeModalVisible = false"
      @start="prepareCalibration"
    />

    <div v-if="!disclaimerAccepted && screen !== 'admin'" class="consent-mask">
      <section class="consent-dialog">
        <h2>使用前确认</h2>
        <p>{{ brand.complianceNotice }}</p>
        <button class="primary" @click="acceptDisclaimer">我已知晓并开始训练</button>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import HomeView from './components/HomeView.vue'
import ModeModal from './components/ModeModal.vue'
import CalibrationView from './components/CalibrationView.vue'
import ChatView from './components/ChatView.vue'
import IncomingCallView from './components/IncomingCallView.vue'
import ActiveCallView from './components/ActiveCallView.vue'
import VideoCallView from './components/VideoCallView.vue'
import ReviewView from './components/ReviewView.vue'
import ReviewDetailView from './components/ReviewDetailView.vue'
import HistoryView from './components/HistoryView.vue'
import ProfileView from './components/ProfileView.vue'
import AdminView from './components/AdminView.vue'
import GamifiedView from './components/GamifiedView.vue'
import { scenes as fallbackScenes, getScene as getFallbackScene } from './data/scenes'
import { clearHistory, loadHistory, saveHistoryItem } from './utils/storage'
import { endChat, fetchBrand, fetchHistory, fetchScenes, fetchVoiceConfig, reportFrontendError, sendMessage, startChat, synthesizeSpeech, transcribeAudio } from './services/api'

const screen = ref(window.location.hash.startsWith('#admin') ? 'admin' : 'home')
const scenes = ref(fallbackScenes)
const pendingScene = ref(fallbackScenes[0])
const pendingMode = ref('text')
const currentSceneId = ref(fallbackScenes[0].id)
const selectedMode = ref('text')
const sessionId = ref('')
const messages = ref([])
const currentReview = ref(fallbackScenes[0].review)
const history = ref(loadHistory())
const riskState = ref({ privacy: 0, property: 0, privacy_delta: 0, property_delta: 0, reason: '', warning: '' })
const quickReplies = ref(fallbackScenes[0].quickReplies)
const voiceSettings = ref({ ttsProvider: 'browser', asrProvider: 'browser', voiceName: '训练角色中性声', voiceGender: 'neutral', rate: 0.95, phoneNumber: '188 **** 8888', location: '未知' })
const disclaimerAccepted = ref(localStorage.getItem('anti_fraud_disclaimer_ok') === '1')
const brand = ref({
  logoUrl: '/assets/hero-shield.png',
  mainTitle: '反诈话术陪练助手',
  subtitle: '沉浸式模拟对话，练就反诈应对能力',
  complianceNotice: '本工具为模拟科普，所有内容均为虚构；如遇真实诈骗，请立即拨打全国反诈专线 96110。'
})
const modeModalVisible = ref(false)
const chatLoading = ref(false)
const chatError = ref('')
const callStartedAt = ref(0)
const callSeconds = ref(28)
const callState = ref('待来电')
let callTimer = null
let recognition = null
let currentUtterance = null
let ringContext = null
let ringOscillator = null
let ttsAudio = null

const currentScene = computed(() => scenes.value.find((scene) => scene.id === currentSceneId.value) || scenes.value[0] || getFallbackScene(currentSceneId.value))
const browserAsrSupported = computed(() => {
  const isSecure = window.location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(window.location.hostname)
  return Boolean(isSecure && window.webkitSpeechRecognition)
})
const cloudAsrSupported = computed(() => {
  const provider = voiceSettings.value.asrProvider
  return Boolean(
    provider &&
    provider !== 'browser' &&
    navigator.mediaDevices?.getUserMedia &&
    (window.AudioContext || window.webkitAudioContext)
  )
})
const asrSupported = computed(() => {
  return browserAsrSupported.value || cloudAsrSupported.value
})
const callTimerLabel = computed(() => {
  const minutes = String(Math.floor(callSeconds.value / 60)).padStart(2, '0')
  const seconds = String(callSeconds.value % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
})

function go(next) {
  stopSpeech()
  stopRecognition()
  stopRinging()
  stopCallTimer()
  screen.value = next
}

function openModeModal(scene) {
  pendingScene.value = scene
  modeModalVisible.value = true
}

function prepareCalibration(mode) {
  modeModalVisible.value = false
  pendingMode.value = mode
  screen.value = 'calibration'
}

async function startChallenge(mode) {
  modeModalVisible.value = false
  selectedMode.value = mode
  currentSceneId.value = pendingScene.value.id
  chatError.value = ''
  chatLoading.value = false
  await loadVoiceSettings(pendingScene.value.id)
  const started = await startChat(pendingScene.value.id, mode)
  sessionId.value = started.session_id
  riskState.value = started.risk || { privacy: 0, property: 0, privacy_delta: 0, property_delta: 0, reason: '', warning: '' }
  quickReplies.value = started.quick_replies?.length ? started.quick_replies : pendingScene.value.quickReplies
  const intro = started.intro || pendingScene.value.intro
  const firstText = intro ? `${intro}\n\n${started.first_message}` : started.first_message
  messages.value = [{ role: 'ai', text: firstText, time: '10:21' }]
  currentReview.value = pendingScene.value.review

  if (mode === 'phone') {
    callState.value = '响铃中'
    screen.value = 'incoming'
    startRinging()
    return
  }
  if (mode === 'video') {
    beginCall()
    screen.value = 'video'
    speak(started.first_message)
    return
  }
  screen.value = 'chat'
}

function acceptCall() {
  stopRinging()
  beginCall()
  screen.value = 'call'
  speakLastAi()
}

function beginCall() {
  callState.value = '通话中'
  callStartedAt.value = Date.now()
  callSeconds.value = 28
  stopCallTimer()
  callTimer = window.setInterval(() => {
    callSeconds.value = Math.max(0, Math.floor((Date.now() - callStartedAt.value) / 1000) + 28)
  }, 1000)
}

async function handleSend(text) {
  if (chatLoading.value || !text.trim()) return
  if (messages.value.length >= 20) {
    chatError.value = '本轮演练已达到最大对话数，请结束挑战查看复盘。'
    return
  }

  chatError.value = ''
  messages.value.push({ role: 'user', text: text.trim() })
  chatLoading.value = true
  try {
    const reply = await sendMessage(sessionId.value, currentSceneId.value, text.trim(), messages.value.length)
    messages.value.push({ role: 'ai', text: reply.ai_reply })
    if (reply.risk) riskState.value = reply.risk
    if (reply.quick_replies?.length) quickReplies.value = reply.quick_replies
    if (selectedMode.value === 'phone' || selectedMode.value === 'video') speak(reply.ai_reply)
  } catch (error) {
    chatError.value = error.message || '网络稍差，请重试'
    reportFrontendError(error, sessionId.value)
  } finally {
    chatLoading.value = false
  }
}

async function finishChallenge() {
  stopSpeech()
  stopRecognition()
  stopRinging()
  stopCallTimer()
  callState.value = '已挂断'
  currentReview.value = await endChat(sessionId.value, currentSceneId.value)
  const record = {
    id: `${Date.now()}-${currentSceneId.value}`,
    sceneId: currentSceneId.value,
    sceneTitle: currentScene.value.title,
    mode: selectedMode.value,
    score: currentReview.value.score,
    level: currentReview.value.level,
    summary: currentReview.value.summary,
    review: currentReview.value,
    messages: messages.value,
    createdAt: new Date().toISOString()
  }
  history.value = saveHistoryItem(record)
  refreshHistory()
  screen.value = 'review'
}

function restartCurrent() {
  pendingScene.value = currentScene.value
  startChallenge(selectedMode.value)
}

function openHistory(record) {
  currentSceneId.value = record.sceneId
  selectedMode.value = record.mode
  currentReview.value = record.review
  messages.value = record.messages || []
  screen.value = 'review'
}

function clearLocalHistory() {
  history.value = clearHistory()
}

function acceptDisclaimer() {
  localStorage.setItem('anti_fraud_disclaimer_ok', '1')
  disclaimerAccepted.value = true
}

function handleBrandUpdated(nextBrand) {
  brand.value = { ...brand.value, ...nextBrand }
}

function speakLastAi() {
  const lastAi = [...messages.value].reverse().find((message) => message.role === 'ai')
  if (lastAi) speak(lastAi.text)
}

async function speak(text) {
  if (!text) return
  if (!['call', 'video'].includes(screen.value) && selectedMode.value !== 'text') return
  stopSpeech()
  stopRecognition()
  callState.value = '播报中'
  if (voiceSettings.value.ttsProvider && voiceSettings.value.ttsProvider !== 'browser') {
    try {
      const result = await synthesizeSpeech(currentSceneId.value, text)
      if (result.audioBase64 && !result.degraded) {
        ttsAudio = new Audio(`data:${result.mimeType};base64,${result.audioBase64}`)
        ttsAudio.playbackRate = Number(voiceSettings.value.rate || 0.95)
        ttsAudio.onended = () => {
          if (screen.value === 'call') callState.value = '通话中'
        }
        await ttsAudio.play()
        return
      }
    } catch (error) {
      reportFrontendError(error, sessionId.value)
    }
  }
  if (!window.speechSynthesis) {
    if (screen.value === 'call') callState.value = '通话中'
    return
  }
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  utterance.rate = Number(voiceSettings.value.rate || 0.95)
  const voices = window.speechSynthesis.getVoices?.() || []
  const preferred = voices.find((voice) => voice.lang?.startsWith('zh') && voice.name?.includes(voiceSettings.value.voiceGender === 'female' ? 'Female' : 'Male'))
    || voices.find((voice) => voice.lang?.startsWith('zh'))
  if (preferred) utterance.voice = preferred
  utterance.onend = () => {
    if (screen.value === 'call') callState.value = '通话中'
  }
  utterance.onerror = () => {
    if (screen.value === 'call') callState.value = '通话中'
  }
  currentUtterance = utterance
  window.speechSynthesis.speak(utterance)
}

function stopSpeech() {
  if (ttsAudio) {
    ttsAudio.pause()
    ttsAudio.src = ''
  }
  ttsAudio = null
  if (window.speechSynthesis) window.speechSynthesis.cancel()
  currentUtterance = null
}

async function startSpeechInput() {
  if (!asrSupported.value) return
  if (callState.value === '播报中' || chatLoading.value) return
  if (cloudAsrSupported.value) {
    stopRecognition()
    callState.value = '识别中'
    try {
      const audioBase64 = await recordPcm16(5200)
      const result = await transcribeAudio(currentSceneId.value, audioBase64)
      const text = result?.text?.trim()
      if (text) {
        await handleSend(text)
      } else {
        chatError.value = result?.degraded ? '语音识别暂不可用，请改用文字回复。' : '没有听清，请再说一遍。'
      }
    } catch (error) {
      chatError.value = '麦克风或语音识别不可用，请改用文字回复。'
      reportFrontendError(error, sessionId.value)
    } finally {
      if (screen.value === 'call') callState.value = '通话中'
    }
    return
  }
  if (!browserAsrSupported.value) return
  stopRecognition()
  callState.value = '识别中'
  const Recognition = window.webkitSpeechRecognition
  recognition = new Recognition()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.maxAlternatives = 1
  recognition.onresult = (event) => {
    const text = event.results?.[0]?.[0]?.transcript
    if (text) handleSend(text)
  }
  recognition.onend = () => {
    if (screen.value === 'call') callState.value = '通话中'
    recognition = null
  }
  recognition.start()
}

async function recordPcm16(durationMs = 5000) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  const audioContext = new AudioContextClass()
  const source = audioContext.createMediaStreamSource(stream)
  const processor = audioContext.createScriptProcessor(4096, 1, 1)
  const chunks = []
  processor.onaudioprocess = (event) => {
    chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
  }
  source.connect(processor)
  processor.connect(audioContext.destination)
  await new Promise((resolve) => window.setTimeout(resolve, durationMs))
  processor.disconnect()
  source.disconnect()
  stream.getTracks().forEach((track) => track.stop())
  await audioContext.close()
  const merged = mergeFloat32(chunks)
  const pcm16 = encodePcm16(downsample(merged, audioContext.sampleRate, 16000))
  return arrayBufferToBase64(pcm16)
}

function mergeFloat32(chunks) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const merged = new Float32Array(length)
  let offset = 0
  chunks.forEach((chunk) => {
    merged.set(chunk, offset)
    offset += chunk.length
  })
  return merged
}

function downsample(buffer, inputRate, outputRate) {
  if (outputRate === inputRate) return buffer
  const ratio = inputRate / outputRate
  const length = Math.round(buffer.length / ratio)
  const result = new Float32Array(length)
  let offsetResult = 0
  let offsetBuffer = 0
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
    let sum = 0
    let count = 0
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      sum += buffer[i]
      count += 1
    }
    result[offsetResult] = count ? sum / count : 0
    offsetResult += 1
    offsetBuffer = nextOffsetBuffer
  }
  return result
}

function encodePcm16(samples) {
  const buffer = new ArrayBuffer(samples.length * 2)
  const view = new DataView(buffer)
  samples.forEach((sample, index) => {
    const clipped = Math.max(-1, Math.min(1, sample))
    view.setInt16(index * 2, clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff, true)
  })
  return buffer
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize))
  }
  return window.btoa(binary)
}

function stopRecognition() {
  if (recognition) {
    recognition.onend = null
    recognition.abort?.()
    recognition.stop?.()
  }
  recognition = null
}

function stopCallTimer() {
  if (callTimer) window.clearInterval(callTimer)
  callTimer = null
}

function startRinging() {
  if (navigator.vibrate) navigator.vibrate([350, 180, 350, 600])
  try {
    ringContext = new (window.AudioContext || window.webkitAudioContext)()
    ringOscillator = ringContext.createOscillator()
    const gain = ringContext.createGain()
    ringOscillator.frequency.value = 880
    gain.gain.value = 0.025
    ringOscillator.connect(gain)
    gain.connect(ringContext.destination)
    ringOscillator.start()
  } catch {
    ringContext = null
    ringOscillator = null
  }
}

function stopRinging() {
  if (navigator.vibrate) navigator.vibrate(0)
  try {
    ringOscillator?.stop()
    ringContext?.close()
  } catch {
    // Audio nodes may already be stopped by the browser.
  }
  ringOscillator = null
  ringContext = null
}

onBeforeUnmount(() => {
  stopSpeech()
  stopRecognition()
  stopRinging()
  stopCallTimer()
})

async function loadVoiceSettings(sceneId) {
  try {
    voiceSettings.value = { ...voiceSettings.value, ...(await fetchVoiceConfig(sceneId)) }
  } catch (error) {
    reportFrontendError(error, sessionId.value)
  }
}

async function refreshHistory() {
  const remoteHistory = await fetchHistory(10)
  if (remoteHistory?.length) history.value = remoteHistory
}

onMounted(async () => {
  const [remoteScenes, remoteBrand] = await Promise.all([fetchScenes(), fetchBrand()])
  if (remoteScenes?.length) {
    scenes.value = remoteScenes
    pendingScene.value = remoteScenes[0]
    currentSceneId.value = remoteScenes[0].id
    quickReplies.value = remoteScenes[0].quickReplies
  }
  if (remoteBrand) brand.value = { ...brand.value, ...remoteBrand }
  refreshHistory()
})
</script>
