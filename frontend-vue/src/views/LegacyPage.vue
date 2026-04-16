<template>
  <div class="space-y-4">
    <div class="rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur p-4">
      <div class="font-bold">{{ t('legacy.title') }}</div>
      <div class="text-sm text-slate-400 mt-1">
        {{ t('legacy.description') }}
      </div>
    </div>

    <div class="rounded-2xl overflow-hidden border border-white/10 bg-slate-900/60">
      <!-- 注意：旧版页面目前由 8080 静态服务提供（python http.server） -->
      <iframe class="w-full min-h-[60vh] md:min-h-[70vh] lg:min-h-[80vh]" :src="legacyUrl"></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const legacyUrl = `${window.location.protocol}//${window.location.hostname}:8080/index-with-errors.html`
</script>

