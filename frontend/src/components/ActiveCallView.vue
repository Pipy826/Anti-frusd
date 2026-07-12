<template>
  <section class="screen call-screen active-call-screen is-active">
    <button class="call-back-btn" @click="$emit('back')">‹</button>
    <button class="call-menu-btn">⠿</button>
    <div class="call-title call-fade-in">
      <h2>{{ scene.modeIdentity }}</h2>
      <p class="call-timer">{{ timer }}</p>
      <span class="call-state-badge" :class="stateBadgeClass">{{ state }}</span>
    </div>
    <div class="avatar-rings active" :class="{ 'call-pulse': state === '通话中' || state === '播报中', 'call-listening-pulse': state === '识别中' }"><span></span></div>
    <div class="wave call-wave-animate" :class="{ 'wave-speaking': state === '播报中', 'wave-listening': state === '识别中', 'wave-idle': state === '通话中' }">
      <i v-for="i in 8" :key="i"></i>
    </div>
    <p class="record-tip call-fade-in-delay">为了保障您的权益，通话可能会被录音</p>

    <!-- Real-time transcript area -->
    <div class="call-transcript call-slide-up">
      <p v-for="message in messages.slice(-3)" :key="`${message.role}-${message.text}`" :class="{ 'transcript-user': message.role === 'user', 'transcript-ai': message.role !== 'user' }">
        <b>{{ message.role === 'user' ? '我' : scene.modeIdentity }}</b>{{ message.text }}
      </p>
      <p v-if="loading" class="transcript-loading">
        <b>{{ scene.modeIdentity }}</b><span class="typing-dots"><i></i><i></i><i></i></span>
      </p>
    </div>

    <!-- Quick reply buttons with dynamic states -->
    <div v-if="showQuickPanel" class="call-quick call-slide-up">
      <button
        v-for="reply in scene.quickReplies.slice(0, 3)"
        :key="reply"
        :disabled="loading || state === '播报中'"
        :class="{ 'btn-active': lastSent === reply }"
        @click="handleQuickReply(reply)"
      >{{ reply }}</button>
    </div>
    <p v-if="error" class="inline-error">{{ error }}</p>

    <!-- Tool buttons with dynamic states -->
    <div class="call-tools call-fade-in-delay2">
      <button
        :class="['tool-btn', { 'tool-active': state === '识别中', 'tool-muted': !asrSupported }]"
        @click="handleListen"
      >
        <span class="tool-icon">
          <svg v-if="state !== '识别中'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
          <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
        </span>
        <small>{{ toolMicLabel }}</small>
        <span v-if="state === '识别中'" class="recording-indicator"></span>
      </button>
      <button
        class="tool-btn"
        :class="{ 'tool-active-green': autoListenEnabled }"
        @click="toggleAutoListen"
      >
        <span class="tool-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        </span>
        <small>{{ autoListenEnabled ? '自动对话' : '手动模式' }}</small>
      </button>
      <button class="tool-btn" @click="showQuickPanel = !showQuickPanel">
        <span class="tool-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </span>
        <small>快捷回复</small>
      </button>
    </div>
    <button class="hangup call-hangup-pulse" @click="$emit('hangup')">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><line x1="23" y1="1" x2="1" y2="23"/></svg>
      <small>挂断</small>
    </button>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  scene: { type: Object, required: true },
  timer: { type: String, required: true },
  state: { type: String, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  asrSupported: { type: Boolean, default: false },
  messages: { type: Array, default: () => [] },
  autoListen: { type: Boolean, default: true }
})
const emit = defineEmits(['back', 'send', 'listen', 'hangup', 'toggle-auto-listen'])

const lastSent = ref('')
const autoListenEnabled = ref(props.autoListen)
const showQuickPanel = ref(true)

const stateBadgeClass = computed(() => {
  switch (props.state) {
    case '播报中': return 'badge-speaking'
    case '识别中': return 'badge-listening'
    case '通话中': return 'badge-idle'
    default: return ''
  }
})

const toolMicLabel = computed(() => {
  if (!props.asrSupported) return '不可用'
  if (props.state === '识别中') return '录音中...'
  return '按住说话'
})

function handleQuickReply(reply) {
  if (props.loading || props.state === '播报中') return
  lastSent.value = reply
  emit('send', reply)
  setTimeout(() => { lastSent.value = '' }, 600)
}

function handleListen() {
  if (!props.asrSupported) return
  if (props.state === '播报中' || props.loading) return
  emit('listen')
}

function toggleAutoListen() {
  autoListenEnabled.value = !autoListenEnabled.value
  emit('toggle-auto-listen', autoListenEnabled.value)
}

// Watch for state changes: auto-listen after AI finishes speaking
watch(() => props.state, (newState, oldState) => {
  if (oldState === '播报中' && newState === '通话中' && autoListenEnabled.value && props.asrSupported) {
    // Small delay then auto-start listening
    setTimeout(() => {
      if (props.state === '通话中' && !props.loading) {
        emit('listen')
      }
    }, 800)
  }
})
</script>

<style scoped>
/* State badge colors */
.badge-speaking { background: rgba(76, 175, 80, 0.2) !important; color: #4caf50 !important; }
.badge-listening { background: rgba(244, 67, 54, 0.2) !important; color: #f44336 !important; }
.badge-idle { background: rgba(34, 199, 128, 0.18) !important; color: #27e09a !important; }

/* Wave states */
.wave-speaking i {
  background: linear-gradient(#4caf50, #2e7d32) !important;
  box-shadow: 0 0 12px rgba(76, 175, 80, 0.9) !important;
  animation-duration: 0.6s !important;
}
.wave-listening i {
  background: linear-gradient(#f44336, #d32f2f) !important;
  box-shadow: 0 0 12px rgba(244, 67, 54, 0.9) !important;
  animation-duration: 0.4s !important;
}
.wave-idle i {
  animation-duration: 2.4s !important;
  opacity: 0.4;
}

/* Listening pulse on avatar */
.call-listening-pulse {
  animation: listening-ring 1s ease-in-out infinite !important;
  border-color: rgba(244, 67, 54, 0.78) !important;
  box-shadow: 0 0 0 18px rgba(244, 67, 54, 0.18), 0 0 0 38px rgba(244, 67, 54, 0.08), inset 0 0 46px rgba(244, 67, 54, 0.25) !important;
}

@keyframes listening-ring {
  0%, 100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.4), 0 0 0 18px rgba(244, 67, 54, 0.18), 0 0 0 38px rgba(244, 67, 54, 0.08), inset 0 0 46px rgba(244, 67, 54, 0.25); }
  50% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0.2), 0 0 0 26px rgba(244, 67, 54, 0.1), 0 0 0 44px rgba(244, 67, 54, 0.04), inset 0 0 46px rgba(244, 67, 54, 0.35); }
}

/* Tool button enhancements */
.tool-btn {
  position: relative;
  width: 82px;
  height: 82px;
  margin: 0 auto;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 42px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}
.tool-btn:active {
  transform: scale(0.92);
  background: rgba(255, 255, 255, 0.2);
}
.tool-active {
  background: rgba(244, 67, 54, 0.2) !important;
  border-color: rgba(244, 67, 54, 0.5) !important;
  animation: tool-pulse 1.5s ease-in-out infinite;
}
.tool-active-green {
  background: rgba(76, 175, 80, 0.15) !important;
  border-color: rgba(76, 175, 80, 0.4) !important;
}
.tool-active-green small {
  color: #4caf50 !important;
}
.tool-muted {
  opacity: 0.4;
  pointer-events: none;
}
.tool-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  line-height: 1;
}
.tool-icon svg {
  display: block;
}
.tool-btn small {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  color: #b0bdd4;
}
.tool-active small {
  color: #f44336;
}

@keyframes tool-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.3); }
  50% { box-shadow: 0 0 0 8px rgba(244, 67, 54, 0); }
}

/* Recording indicator */
.recording-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f44336;
  animation: rec-blink 1s infinite;
}
@keyframes rec-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Quick reply button active state */
.call-quick button {
  transition: all 0.2s ease;
}
.call-quick button:active:not(:disabled) {
  transform: scale(0.93);
  background: rgba(255, 255, 255, 0.7);
}
.btn-active {
  background: var(--blue) !important;
  color: #fff !important;
  transform: scale(0.95);
}
.call-quick button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Transcript enhancements */
.transcript-user b { color: #4caf50; }
.transcript-ai b { color: #2196f3; }
.transcript-loading {
  color: #8a9bb5;
}
.typing-dots {
  display: inline-flex;
  gap: 3px;
  margin-left: 4px;
  vertical-align: middle;
}
.typing-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #8a9bb5;
  animation: dots-bounce 1.2s infinite;
}
.typing-dots i:nth-child(2) { animation-delay: 0.2s; }
.typing-dots i:nth-child(3) { animation-delay: 0.4s; }
@keyframes dots-bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}
</style>
