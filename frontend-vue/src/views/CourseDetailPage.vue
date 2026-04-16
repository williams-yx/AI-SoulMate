<template>
  <div class="space-y-6">
    <button class="text-slate-400 hover:text-white text-sm" type="button" @click="router.push('/courses')">
      {{ t('courseDetail.backToCourses') }}
    </button>

    <div v-if="loading" class="text-slate-400">{{ t('courseDetail.loading') }}</div>
    <div v-else-if="error" class="text-red-300">{{ errorDisplay }}</div>

    <div v-else-if="course" class="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
      <section class="panel p-6">
        <div class="aspect-video rounded-xl border border-slate-700 bg-slate-900 overflow-hidden relative mb-6">
          <img
            class="w-full h-full object-cover opacity-60"
            src="https://images.unsplash.com/photo-1635324234799-d8c9733d3c87?q=80&w=1000&auto=format&fit=crop"
            alt="course cover"
          />
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="w-16 h-16 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
              ▶
            </div>
          </div>
        </div>

        <div class="text-3xl font-bold">{{ course.title }}</div>
        <div class="mt-2 text-slate-400">{{ course.description }}</div>

        <div class="mt-8 panel2 p-6">
          <div class="font-bold mb-4">{{ t('courseDetail.outlineTitle') }}</div>
          <div class="space-y-3">
            <div class="row">
              <div class="text-slate-200">{{ t('courseDetail.outlineItem1') }}</div>
              <div class="tag">{{ t('courseDetail.preview') }}</div>
            </div>
            <div class="row">
              <div class="text-slate-200">{{ t('courseDetail.outlineItem2') }}</div>
              <div class="lock">{{ t('courseDetail.locked') }}</div>
            </div>
          </div>
        </div>
      </section>

      <aside class="panel p-6 h-fit lg:sticky lg:top-24">
        <div class="text-xs text-slate-500">{{ t('courseDetail.level') }}</div>
        <div class="font-bold text-indigo-300">{{ course.level }}</div>

        <div class="mt-4 text-3xl font-bold text-white">¥ {{ course.price }}</div>
        <button class="btn-primary w-full mt-4" type="button" @click="enroll">
          {{ t('courseDetail.enrollNow') }}
        </button>

        <div class="mt-4 pt-4 border-t border-slate-700 text-xs text-slate-500 space-y-2">
          <div>{{ t('courseDetail.benefitHardware') }}</div>
          <div>{{ t('courseDetail.benefitReplay') }}</div>
          <div>{{ t('courseDetail.duration', { hours: course.duration_hours }) }}</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'

const router = useRouter()
const props = defineProps<{ id: string }>()

type Course = { id: string; title: string; description: string; level: string; price: number; duration_hours: number }

const { t } = useI18n()

const loading = ref(false)
const error = ref('')
const course = ref<Course | null>(null)

const errorDisplay = computed(() => {
  const v = error.value
  return typeof v === 'string' && v.startsWith('courseDetail.') ? t(v) : v
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const list = await api.courses.list()
    course.value = list.find((c) => c.id === props.id) || null
    if (!course.value) error.value = 'courseDetail.notFound'
  } catch (e: any) {
    error.value = e?.message || 'courseDetail.loadFailed'
  } finally {
    loading.value = false
  }
}

function enroll() {
  // 下一步：对接报名/权限/订单
  alert(t('courseDetail.enrollSuccess'))
}

onMounted(load)
</script>

<style scoped>
.panel {
  @apply rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur;
}
.panel2 {
  @apply rounded-xl border border-slate-700 bg-slate-950/30;
}
.btn-primary {
  @apply py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 text-white font-bold shadow-lg shadow-indigo-500/20;
}
.row {
  @apply flex items-center justify-between p-3 rounded bg-slate-900/60 border border-slate-700;
}
.tag {
  @apply text-xs text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded;
}
.lock {
  @apply text-xs text-slate-500;
}
</style>

