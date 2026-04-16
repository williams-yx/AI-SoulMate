<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const router = useRouter()
const { t } = useI18n()

onMounted(() => {
  // 延迟一下，显示提示信息
  setTimeout(() => {
    // 跳转到个人中心，带上充值成功标记
    router.push('/profile?recharge_success=1')
  }, 1000)
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <div class="text-center">
      <div class="mb-4">
        <svg class="w-16 h-16 mx-auto text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h1 class="text-2xl font-bold text-white mb-2">{{ t('rechargeCallback.success') }}</h1>
      <p class="text-slate-400">{{ t('rechargeCallback.redirecting') }}</p>
    </div>
  </div>
</template>
