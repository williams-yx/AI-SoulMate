<template>
  <!-- 按旧版 tpl-courses 还原课程列表样式 -->
  <div class="page-transition">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold flex items-center gap-2">
        <i data-lucide="sparkles" class="w-5 h-5 text-indigo-400"></i>
        {{ t('courses.title') }}
      </h2>
      <button class="btn-refresh" type="button" @click="load">{{ t('courses.refresh') }}</button>
    </div>

    <div v-if="loading" class="text-slate-400">{{ t('courses.loading') }}</div>
    <div v-else-if="error" class="text-red-300">{{ error }}</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 所有课程统一使用旧版中间 L2 推荐卡片的美化样式 -->
      <RouterLink
        v-for="c in courses"
        :key="c.id"
        class="block"
        :to="`/courses/${c.id}`"
      >
        <div
          class="glass-panel p-0 rounded-2xl overflow-hidden group border border-indigo-500/40 shadow-lg shadow-indigo-500/10 cursor-pointer flex flex-col transform transition duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-indigo-500/20 hover:border-indigo-400"
        >
          <div class="bg-gradient-to-br from-indigo-900 to-slate-900 p-6 relative">
            <div class="absolute top-4 right-4 bg-indigo-500 text-xs font-bold px-2 py-1 rounded shadow">
              {{ t('courses.recommendedTag') }}
            </div>
            <div class="text-xs text-indigo-200 opacity-80 mb-1">
              {{ c.level }}
            </div>
            <h3 class="text-xl font-bold text-white relative z-10">{{ c.title }}</h3>
            <p class="text-indigo-200 text-sm mt-1 relative z-10 line-clamp-2">
              {{ c.description }}
            </p>
            <i
              data-lucide="box"
              class="absolute bottom-4 right-4 w-16 h-16 text-white/5 group-hover:rotate-12 transition"
            ></i>
          </div>
          <div class="p-6 bg-slate-900/40 flex-1 flex flex-col">
            <ul class="space-y-2 mb-6 text-sm text-slate-400">
              <li class="flex gap-2">
                <i data-lucide="check" class="w-4 h-4 text-emerald-500"></i>
                {{ t('courses.featurePbl') }}
              </li>
              <li class="flex gap-2">
                <i data-lucide="check" class="w-4 h-4 text-emerald-500"></i>
                {{ t('courses.featureKit') }}
              </li>
            </ul>
            <div class="mt-auto flex justify-between items-center">
              <span class="text-lg font-bold text-emerald-400">¥ {{ c.price }}</span>
              <span class="text-sm font-bold text-indigo-400 group-hover:translate-x-1 transition">{{ t('courses.outline') }}</span>
            </div>
          </div>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'

type Course = { id: string; title: string; description: string; level: string; price: number; duration_hours: number }

const loading = ref(false)
const error = ref('')
const courses = ref<Course[]>([])

const { t } = useI18n()

async function load() {
  loading.value = true
  error.value = ''
  try {
    courses.value = await api.courses.list()
  } catch (e: any) {
    error.value = e?.message || t('courses.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-transition {
  @apply animate-[slideUp_0.3s_cubic-bezier(0.16,1,0.3,1)];
}
.btn-refresh {
  @apply px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm;
}
</style>

