/**
 * 电话音效处理器 — 模拟真实电话通话音质
 *
 * 特性：
 * 1. 带通滤波器 (300Hz - 3400Hz) 模拟电话带宽
 * 2. 轻微失真/压缩 模拟电话线路
 * 3. 可选背景噪声叠加
 * 4. 通话接通/挂断提示音
 */

let audioContext = null
let phoneFilterChain = null

function getAudioContext() {
  if (!audioContext || audioContext.state === 'closed') {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    audioContext = new AudioContextClass()
  }
  if (audioContext.state === 'suspended') {
    audioContext.resume()
  }
  return audioContext
}

/**
 * 创建电话音效滤波链
 * 真实电话的频率范围是 300Hz - 3400Hz，加上轻微的压缩和失真
 */
function createPhoneFilterChain(ctx) {
  // 高通滤波器 — 切掉 300Hz 以下的低频
  const highpass = ctx.createBiquadFilter()
  highpass.type = 'highpass'
  highpass.frequency.value = 300
  highpass.Q.value = 0.7

  // 低通滤波器 — 切掉 3400Hz 以上的高频
  const lowpass = ctx.createBiquadFilter()
  lowpass.type = 'lowpass'
  lowpass.frequency.value = 3400
  lowpass.Q.value = 0.7

  // 峰值滤波器 — 增强 1kHz-2kHz 中频（电话人声频段）
  const peaking = ctx.createBiquadFilter()
  peaking.type = 'peaking'
  peaking.frequency.value = 1500
  peaking.Q.value = 1.0
  peaking.gain.value = 3

  // 动态压缩器 — 模拟电话线路的动态压缩
  const compressor = ctx.createDynamicsCompressor()
  compressor.threshold.value = -24
  compressor.knee.value = 12
  compressor.ratio.value = 4
  compressor.attack.value = 0.003
  compressor.release.value = 0.15

  // 轻微增益补偿
  const gainNode = ctx.createGain()
  gainNode.gain.value = 1.1

  // 连接滤波链
  highpass.connect(lowpass)
  lowpass.connect(peaking)
  peaking.connect(compressor)
  compressor.connect(gainNode)

  return { input: highpass, output: gainNode }
}

/**
 * 通过电话滤波器播放音频
 * @param {string} audioDataUrl - data:audio/mpeg;base64,xxx 格式的音频 URL
 * @param {object} options - 播放选项
 * @param {number} options.playbackRate - 播放速率（默认 1.0）
 * @param {boolean} options.phoneEffect - 是否启用电话音效（默认 true）
 * @param {function} options.onEnded - 播放结束回调
 * @returns {object} 控制对象 { stop(), isPlaying }
 */
export async function playWithPhoneEffect(audioDataUrl, options = {}) {
  const {
    playbackRate = 1.0,
    phoneEffect = true,
    onEnded = null
  } = options

  // 如果不需要电话音效，直接用 Audio 播放
  if (!phoneEffect) {
    const audio = new Audio(audioDataUrl)
    audio.playbackRate = playbackRate
    if (onEnded) audio.onended = onEnded
    await audio.play()
    return {
      stop: () => { audio.pause(); audio.src = '' },
      get isPlaying() { return !audio.paused }
    }
  }

  const ctx = getAudioContext()

  // 加载音频数据
  const response = await fetch(audioDataUrl)
  const arrayBuffer = await response.arrayBuffer()
  const audioBuffer = await ctx.decodeAudioData(arrayBuffer)

  // 创建音频源
  const source = ctx.createBufferSource()
  source.buffer = audioBuffer
  source.playbackRate.value = playbackRate

  // 创建电话滤波链
  const chain = createPhoneFilterChain(ctx)

  // 添加轻微底噪（模拟电话线路噪声）
  const noiseGain = ctx.createGain()
  noiseGain.gain.value = 0.003 // 非常轻微的底噪
  const noiseBuffer = createNoiseBuffer(ctx, audioBuffer.duration)
  const noiseSource = ctx.createBufferSource()
  noiseSource.buffer = noiseBuffer
  noiseSource.connect(noiseGain)

  // 最终混合输出
  const masterGain = ctx.createGain()
  masterGain.gain.value = 1.0

  // 连接：source → 电话滤波链 → master
  source.connect(chain.input)
  chain.output.connect(masterGain)
  noiseGain.connect(masterGain)
  masterGain.connect(ctx.destination)

  // 播放
  source.start(0)
  noiseSource.start(0)

  let stopped = false
  source.onended = () => {
    if (!stopped) {
      stopped = true
      try { noiseSource.stop() } catch { /* already stopped */ }
      if (onEnded) onEnded()
    }
  }

  return {
    stop: () => {
      if (!stopped) {
        stopped = true
        try { source.stop() } catch { /* already stopped */ }
        try { noiseSource.stop() } catch { /* already stopped */ }
        if (onEnded) onEnded()
      }
    },
    get isPlaying() { return !stopped }
  }
}

/**
 * 生成白噪声 buffer（模拟电话底噪）
 */
function createNoiseBuffer(ctx, duration) {
  const sampleRate = ctx.sampleRate
  const length = Math.ceil(sampleRate * duration)
  const buffer = ctx.createBuffer(1, length, sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i++) {
    // 布朗噪声（比白噪声更低沉，更像电话底噪）
    data[i] = (Math.random() * 2 - 1) * 0.5
    if (i > 0) {
      data[i] = data[i - 1] * 0.98 + data[i] * 0.02
    }
  }
  return buffer
}

/**
 * 播放电话接通音 — 模拟真实手机接通时的短促提示音
 */
export function playConnectTone() {
  const ctx = getAudioContext()
  const now = ctx.currentTime

  // 真实接通音：一声短促的中频提示音（类似"嘟"）
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.value = 480
  gain.gain.setValueAtTime(0.04, now)
  gain.gain.linearRampToValueAtTime(0, now + 0.12)
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start(now)
  osc.stop(now + 0.15)
}

/**
 * 播放电话挂断音 — 模拟真实电话挂断后的忙音
 * 标准忙音：450Hz + 间隔，短促两声
 */
export function playHangupTone() {
  const ctx = getAudioContext()
  const now = ctx.currentTime

  // 两声短促的忙音（比三声更自然）
  const times = [0, 0.25]
  times.forEach((offset) => {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = 450
    gain.gain.setValueAtTime(0.035, now + offset)
    gain.gain.setValueAtTime(0.035, now + offset + 0.15)
    gain.gain.linearRampToValueAtTime(0, now + offset + 0.18)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(now + offset)
    osc.stop(now + offset + 0.2)
  })
}

/**
 * 播放等待对方接听的回铃音
 * 中国标准回铃音：450Hz，响1秒停4秒
 * @returns {function} stop 函数
 */
export function playRingbackTone() {
  const ctx = getAudioContext()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()

  osc.type = 'sine'
  osc.frequency.value = 450
  gain.gain.value = 0

  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start()

  let running = true
  function schedule() {
    if (!running) return
    const now = ctx.currentTime
    // 响1秒
    gain.gain.setValueAtTime(0.035, now)
    gain.gain.setValueAtTime(0.035, now + 1.0)
    // 停4秒
    gain.gain.linearRampToValueAtTime(0, now + 1.05)
    gain.gain.setValueAtTime(0, now + 5.0)
    setTimeout(schedule, 5000)
  }
  schedule()

  return () => {
    running = false
    try { gain.gain.cancelScheduledValues(0); gain.gain.value = 0 } catch { /* ok */ }
    try { osc.stop() } catch { /* already stopped */ }
  }
}

/**
 * 清理音频上下文
 */
export function disposeAudioContext() {
  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close()
  }
  audioContext = null
}
