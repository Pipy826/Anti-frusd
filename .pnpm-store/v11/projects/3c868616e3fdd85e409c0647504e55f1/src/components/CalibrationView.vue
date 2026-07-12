<template>
  <section class="screen calibration-screen is-active">
    <header class="simple-head">
      <button class="icon-btn" @click="$emit('back')">‹</button>
      <h2>认知校准</h2>
      <span></span>
    </header>

    <div class="calibration-intro">
      <h1>{{ scene.title }}</h1>
      <p>先用 3 道判断题热身一下。答题结果不影响进入训练，只帮助你带着更真实的心态开始。</p>
    </div>

    <div class="calibration-list">
      <article v-for="(question, index) in questions" :key="question.id" class="calibration-card">
        <b>第 {{ index + 1 }} 题</b>
        <h3>{{ question.question }}</h3>
        <button
          v-for="option in question.options"
          :key="option"
          :class="{ picked: answers[question.id] === option, correct: submitted && option === resultMap[question.id]?.answer, wrong: submitted && answers[question.id] === option && option !== resultMap[question.id]?.answer }"
          @click="!submitted && (answers[question.id] = option)"
        >
          {{ option }}
        </button>
        <p v-if="submitted" class="explain">{{ resultMap[question.id]?.explanation }}</p>
      </article>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <div class="calibration-actions">
      <p v-if="submitted">答对 {{ result.correct }} / {{ result.total }} 题</p>
      <button v-if="!submitted" class="primary" :disabled="!ready || loading" @click="submit">提交并查看</button>
      <button v-else class="primary" @click="$emit('continue')">进入训练</button>
      <button v-if="!submitted" class="outline compact" @click="$emit('continue')">跳过，直接训练</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { reportFrontendError, submitCognitive } from '../services/api'

const props = defineProps({
  scene: { type: Object, required: true }
})
const emit = defineEmits(['back', 'continue'])

const questions = computed(() => props.scene.cognitiveQuestions?.length ? props.scene.cognitiveQuestions.slice(0, 3) : fallbackQuestions.value)
const answers = ref({})
const loading = ref(false)
const submitted = ref(false)
const result = ref({ total: 0, correct: 0, wrong: 0, details: [] })
const error = ref('')
const fallbackQuestions = ref([
  {
    id: 'fallback-q1',
    question: '涉及转账、验证码、陌生链接时，第一反应应该是什么？',
    options: ['先暂停并核实', '马上配合', '看对方语气决定']
  },
  {
    id: 'fallback-q2',
    question: '对方制造紧急和保密压力时，通常意味着什么？',
    options: ['需要更警惕', '说明更可信', '可以跳过核验']
  },
  {
    id: 'fallback-q3',
    question: '遇到真实诈骗线索，可以拨打哪个反诈专线？',
    options: ['96110', '任意陌生号码', '对方提供的号码']
  }
])

const ready = computed(() => questions.value.every((question) => answers.value[question.id]))
const resultMap = computed(() => Object.fromEntries((result.value.details || []).map((item) => [item.id, item])))

async function submit() {
  if (!ready.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    result.value = await submitCognitive(
      props.scene.id,
      questions.value.map((question) => ({ questionId: question.id, answer: answers.value[question.id] }))
    )
    submitted.value = true
  } catch (err) {
    error.value = err.message || '认知校准提交失败'
    reportFrontendError(err)
  } finally {
    loading.value = false
  }
}
</script>
