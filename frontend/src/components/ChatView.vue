<template>
  <section class="screen chat-screen is-active">
    <header class="chat-head">
      <button class="icon-btn" @click="$emit('back')">‹</button>
      <h2>{{ scene.title }}</h2>
      <button class="danger" :class="{ 'btn-pulse': risk.privacy >= 50 || risk.property >= 50 }" @click="$emit('end')">结束挑战</button>
    </header>
    <div class="time-pill">10:21</div>
    <!-- Phase indicator -->
    <div class="phase-indicator" :class="`phase-${phase}`">
      <span class="phase-dot"></span>
      <span class="phase-label">{{ phaseLabel }}</span>
    </div>
    <div class="risk-panel" :class="{ 'risk-high': risk.privacy >= 50 || risk.property >= 50 }">
      <div>
        <span>个人信息泄露风险</span>
        <b :class="{ 'risk-value-warn': risk.privacy >= 40, 'risk-value-danger': risk.privacy >= 60 }">{{ risk.privacy }}%</b>
        <i><em :style="{ width: `${risk.privacy}%` }" :class="riskBarClass(risk.privacy)"></em></i>
      </div>
      <div>
        <span>财产损失风险</span>
        <b :class="{ 'risk-value-warn': risk.property >= 40, 'risk-value-danger': risk.property >= 60 }">{{ risk.property }}%</b>
        <i><em :style="{ width: `${risk.property}%` }" :class="riskBarClass(risk.property)"></em></i>
      </div>
      <p v-if="risk.warning" class="risk-warning-text">{{ risk.warning }}</p>
    </div>
    <!-- Consequence alert -->
    <transition name="alert-fade">
      <div v-if="consequenceAlert" class="consequence-alert">
        <p v-for="(line, idx) in consequenceAlertLines" :key="idx">{{ line }}</p>
        <button class="alert-dismiss" @click="$emit('dismiss-alert')">知道了</button>
      </div>
    </transition>
    <div ref="messageBox" class="messages">
      <div v-for="(message, index) in messages" :key="`${index}-${message.text}`" :class="['msg', message.role === 'user' ? 'me' : 'ai']">
        <img v-if="message.role !== 'user'" src="/assets/bot.png" alt="">
        <div v-if="message.role !== 'user'" class="ai-bubble">
          <!-- Role label badge -->
          <span v-if="message.roleLabel" class="role-badge">{{ message.roleLabel }}</span>
          <p>
            <template v-for="(part, partIndex) in tokenizeMessage(message.text)" :key="`${index}-${partIndex}`">
              <span v-if="part.type === 'media'" class="media-placeholder" :class="`media-${part.mediaType}`">
                <span class="media-icon">{{ mediaIcon(part.mediaType) }}</span>
                <span class="media-text">{{ part.text }}</span>
              </span>
              <span v-else-if="part.type === 'token'" class="message-token">{{ part.text }}</span>
              <span v-else>{{ part.text }}</span>
            </template>
            <button class="bubble-speak" @click="$emit('speak', message.text)">▶</button>
          </p>
        </div>
        <p v-if="message.role === 'user'">
          <template v-for="(part, partIndex) in tokenizeMessage(message.text)" :key="`${index}-${partIndex}`">
            <span :class="{ 'message-token': part.type === 'token' }">{{ part.text }}</span>
          </template>
        </p>
        <img v-if="message.role === 'user'" src="/assets/user.png" alt="">
      </div>
      <div v-if="loading" class="typing">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-text">对方正在输入</span>
      </div>
    </div>
    <p v-if="error" class="inline-error">{{ error }}</p>
    <!-- Quick replies with dynamic states -->
    <div class="quick" :class="{ 'quick-disabled': loading }">
      <button
        v-for="reply in visibleQuickReplies"
        :key="reply"
        :disabled="loading"
        :class="{ 'quick-btn-sent': lastQuickReply === reply }"
        @click="handleQuickReply(reply)"
      >
        <span class="quick-text">{{ reply }}</span>
        <span v-if="lastQuickReply === reply" class="quick-check">✓</span>
      </button>
    </div>
    <form :class="['composer', { compact: !asrSupported, 'composer-loading': loading }]" @submit.prevent="submit">
      <button
        v-if="asrSupported"
        type="button"
        class="round mic-btn"
        :class="{ 'mic-active': isListening }"
        @click="$emit('listen')"
        :disabled="loading"
      >
        <span>{{ isListening ? '●' : '♩' }}</span>
      </button>
      <input
        v-model="draft"
        placeholder="输入您的回复..."
        autocomplete="off"
        :disabled="loading"
        @focus="inputFocused = true"
        @blur="inputFocused = false"
      >
      <button
        class="primary send"
        :disabled="!draft.trim() || loading"
        :class="{ 'send-ready': draft.trim() && !loading, 'send-loading': loading }"
      >
        <span v-if="!loading">发送</span>
        <span v-else class="send-spinner"></span>
      </button>
    </form>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  scene: { type: Object, required: true },
  messages: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  risk: { type: Object, required: true },
  quickReplies: { type: Array, default: () => [] },
  asrSupported: { type: Boolean, default: false },
  phase: { type: String, default: 'trust_building' },
  consequenceAlert: { type: String, default: '' }
})
const emit = defineEmits(['back', 'send', 'end', 'speak', 'listen', 'dismiss-alert'])
const draft = ref('')
const messageBox = ref(null)
const lastQuickReply = ref('')
const inputFocused = ref(false)
const isListening = ref(false)
const visibleQuickReplies = computed(() => (props.quickReplies.length ? props.quickReplies : props.scene.quickReplies).slice(0, 4))

const PHASE_LABELS = {
  trust_building: '对方正在建立信任',
  urgency_creation: '对方开始制造紧迫感',
  action_induction: '对方正在诱导操作',
  escape_blocking: '对方试图阻止你核验'
}
const phaseLabel = computed(() => PHASE_LABELS[props.phase] || '对话进行中')

const consequenceAlertLines = computed(() => (props.consequenceAlert || '').split('\n').filter(Boolean))

watch(() => props.messages.length, async () => {
  await nextTick()
  if (messageBox.value) messageBox.value.scrollTop = messageBox.value.scrollHeight
})

// Reset listening state when loading changes
watch(() => props.loading, (loading) => {
  if (loading) isListening.value = false
})

function submit() {
  const text = draft.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  draft.value = ''
}

function handleQuickReply(reply) {
  if (props.loading) return
  lastQuickReply.value = reply
  draft.value = reply
  // Auto-send after brief visual feedback
  setTimeout(() => {
    emit('send', reply)
    draft.value = ''
    setTimeout(() => { lastQuickReply.value = '' }, 400)
  }, 150)
}

function riskBarClass(value) {
  if (value >= 60) return 'risk-bar-danger'
  if (value >= 40) return 'risk-bar-warn'
  return ''
}

// Media type detection for multimedia placeholders
const MEDIA_PATTERNS = [
  { regex: /【语音[^】]*】/, type: 'voice' },
  { regex: /【图片[：:][^】]*】/, type: 'image' },
  { regex: /【视频[^】]*】/, type: 'video' },
  { regex: /【截图[：:][^】]*】/, type: 'image' },
  { regex: /【链接[：:][^】]*】/, type: 'link' },
  { regex: /【文件[：:][^】]*】/, type: 'file' },
  { regex: /【录音[^】]*】/, type: 'voice' }
]

function tokenizeMessage(text = '') {
  const parts = String(text)
    .split(/(【[^】]+】)/g)
    .filter(Boolean)

  return parts.map((part) => {
    if (!/^【[^】]+】$/.test(part)) {
      return { text: part, type: 'text' }
    }
    for (const pattern of MEDIA_PATTERNS) {
      if (pattern.regex.test(part)) {
        return { text: part.slice(1, -1), type: 'media', mediaType: pattern.type }
      }
    }
    if (/^【(链接|图片|语音|视频|截图|文件|录音|视频画面)】$/.test(part)) {
      const typeMap = { '链接': 'link', '图片': 'image', '语音': 'voice', '视频': 'video', '截图': 'image', '文件': 'file', '录音': 'voice', '视频画面': 'video' }
      const inner = part.slice(1, -1)
      return { text: inner, type: 'media', mediaType: typeMap[inner] || 'file' }
    }
    return { text: part, type: 'token' }
  })
}

function mediaIcon(mediaType) {
  const icons = { voice: '🎙', image: '🖼', video: '🎬', link: '🔗', file: '📄' }
  return icons[mediaType] || '📎'
}
</script>

<style scoped>
/* Phase indicator */
.phase-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  margin: 0 16px 6px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.06);
  color: #8a9bb5;
  transition: all 0.4s ease;
}
.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4caf50;
  animation: pulse-dot 2s infinite;
}
.phase-urgency_creation .phase-dot { background: #ff9800; }
.phase-action_induction .phase-dot { background: #f44336; }
.phase-escape_blocking .phase-dot { background: #9c27b0; }
.phase-urgency_creation { color: #ff9800; }
.phase-action_induction { color: #f44336; }
.phase-escape_blocking { color: #9c27b0; }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

/* Risk panel enhancements */
.risk-high {
  border: 1px solid rgba(244, 67, 54, 0.3) !important;
  animation: risk-flash 2s ease-in-out infinite;
}
@keyframes risk-flash {
  0%, 100% { background: rgba(244, 67, 54, 0.03); }
  50% { background: rgba(244, 67, 54, 0.08); }
}
.risk-value-warn { color: #ff9800 !important; }
.risk-value-danger { color: #f44336 !important; font-weight: 700; }
.risk-bar-warn { background: linear-gradient(90deg, #ff9800, #ffc107) !important; }
.risk-bar-danger { background: linear-gradient(90deg, #f44336, #ff5722) !important; }
.risk-warning-text { color: #f44336; font-weight: 600; }

/* End challenge button pulse when high risk */
.btn-pulse {
  animation: danger-pulse 1.5s ease-in-out infinite;
}
@keyframes danger-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 64, 72, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(255, 64, 72, 0); }
}

/* Consequence alert */
.consequence-alert {
  margin: 6px 16px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(244, 67, 54, 0.08);
  border: 1px solid rgba(244, 67, 54, 0.25);
  font-size: 12.5px;
  line-height: 1.6;
  color: #d32f2f;
}
.consequence-alert p { margin: 0 0 4px; }
.consequence-alert p:last-of-type { margin-bottom: 8px; }
.alert-dismiss {
  display: inline-block;
  padding: 2px 10px;
  border: 1px solid rgba(244, 67, 54, 0.3);
  border-radius: 6px;
  background: transparent;
  color: #d32f2f;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}
.alert-dismiss:hover { background: rgba(244, 67, 54, 0.1); }
.alert-fade-enter-active, .alert-fade-leave-active { transition: all 0.3s ease; }
.alert-fade-enter-from, .alert-fade-leave-to { opacity: 0; transform: translateY(-8px); }

/* AI bubble with role label */
.ai-bubble { position: relative; display: inline-block; }
.role-badge {
  display: inline-block;
  padding: 1px 8px;
  margin-bottom: 4px;
  border-radius: 8px;
  background: rgba(18, 108, 255, 0.12);
  color: #126cff;
  font-size: 11px;
  font-weight: 500;
}

/* Multimedia placeholder cards */
.media-placeholder {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  margin: 2px 0;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  font-size: 12.5px;
  color: #53617a;
  vertical-align: middle;
  transition: all 0.2s;
}
.media-placeholder:hover { transform: scale(1.02); }
.media-placeholder.media-voice { background: rgba(76, 175, 80, 0.08); border-color: rgba(76, 175, 80, 0.2); }
.media-placeholder.media-video { background: rgba(156, 39, 176, 0.08); border-color: rgba(156, 39, 176, 0.2); }
.media-placeholder.media-link { background: rgba(255, 152, 0, 0.08); border-color: rgba(255, 152, 0, 0.2); color: #e65100; }
.media-placeholder.media-image { background: rgba(33, 150, 243, 0.08); border-color: rgba(33, 150, 243, 0.2); }
.media-icon { font-size: 14px; }
.media-text { font-size: 12px; }

/* Enhanced typing indicator */
.typing {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  color: #8a9bb5;
  font-size: 13px;
}
.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8a9bb5;
  animation: typing-bounce 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
.typing-text { margin-left: 4px; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* Quick reply buttons enhanced */
.quick {
  transition: opacity 0.3s;
}
.quick-disabled {
  opacity: 0.6;
  pointer-events: none;
}
.quick button {
  position: relative;
  overflow: hidden;
  transition: all 0.2s ease;
}
.quick button:active:not(:disabled) {
  transform: scale(0.93);
}
.quick button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.quick-btn-sent {
  background: var(--blue) !important;
  color: #fff !important;
  transform: scale(0.95);
}
.quick-text { position: relative; z-index: 1; }
.quick-check {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: #fff;
  animation: check-pop 0.3s ease;
}
@keyframes check-pop {
  from { transform: translateY(-50%) scale(0); }
  to { transform: translateY(-50%) scale(1); }
}

/* Composer / input area */
.composer {
  transition: opacity 0.3s;
}
.composer-loading {
  opacity: 0.85;
}
.composer input:disabled {
  opacity: 0.7;
}

/* Send button states */
.send {
  transition: all 0.2s ease;
  min-width: 52px;
}
.send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.send-ready {
  background: var(--blue) !important;
  transform: scale(1);
  box-shadow: 0 2px 8px rgba(18, 108, 255, 0.4);
}
.send-ready:active {
  transform: scale(0.92);
}
.send-loading {
  pointer-events: none;
}
.send-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Mic button */
.mic-btn {
  transition: all 0.2s ease;
}
.mic-btn:active {
  transform: scale(0.9);
}
.mic-active {
  background: rgba(244, 67, 54, 0.15) !important;
  color: #f44336 !important;
  animation: mic-pulse 1.5s infinite;
}
@keyframes mic-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.3); }
  50% { box-shadow: 0 0 0 6px rgba(244, 67, 54, 0); }
}
</style>
