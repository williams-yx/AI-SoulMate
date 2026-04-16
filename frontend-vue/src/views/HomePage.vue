<template>
  <!-- 完整照搬旧版 tpl-home 的结构，只把跳转方式改成 RouterLink -->
  <div class="page-transition flex flex-col">
    <div class="flex-1">
      <div class="text-center py-10 md:py-16">
        <h1 class="text-4xl md:text-7xl font-bold mb-6 tracking-tight text-white leading-tight">
          {{ t('home.heroTitleLine1') }} <br /><span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">{{ t('home.heroTitleHighlight') }}</span>
        </h1>
        <p class="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 px-2">{{ t('home.heroDescription') }}</p>
      </div>

      <!-- 旧版首页中的「快速开始」区域 -->
      <div class="mt-10 glass-panel p-6 rounded-2xl">
        <h2 class="text-xl font-semibold mb-4">{{ t('home.quickStartTitle') }}</h2>
        <div class="space-y-3">
          <div class="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
            <div>
              <h3 class="font-semibold">{{ t('home.features.textToImage.title') }}</h3>
              <p class="text-sm text-slate-400">{{ t('home.features.textToImage.description') }}</p>
            </div>
            <RouterLink :to="{ path: '/studio', query: { mode: 'text2image' } }" class="ml-4 inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded">
              {{ t('home.quickStartButton') }}
            </RouterLink>
          </div>
          <div class="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
            <div>
              <h3 class="font-semibold">{{ t('home.features.textTo3d.title') }}</h3>
              <p class="text-sm text-slate-400">{{ t('home.features.textTo3d.description') }}</p>
            </div>
            <RouterLink :to="{ path: '/studio', query: { mode: 'text23d' } }" class="ml-4 inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded">
              {{ t('home.quickStartButton') }}
            </RouterLink>
          </div>
          <div class="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
            <div>
              <h3 class="font-semibold">{{ t('home.features.imageTo3d.title') }}</h3>
              <p class="text-sm text-slate-400">{{ t('home.features.imageTo3d.description') }}</p>
            </div>
            <RouterLink :to="{ path: '/studio', query: { mode: 'image23d' } }" class="ml-4 inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded">
              {{ t('home.quickStartButton') }}
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- 首页底部：多栏 + 备案条（参考站外版式） -->
    <footer class="mt-16 w-full border-t border-white/[0.06] bg-slate-950 text-slate-300">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-10 md:py-12">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-8">
          <!-- 品牌 + 简介 -->
          <div id="about-company" class="scroll-mt-24">
            <div class="flex items-start gap-3 mb-4">
              <div
                class="w-11 h-11 shrink-0 flex items-center justify-center rounded-xl bg-indigo-500/20 border border-indigo-500/35"
              >
                <i data-lucide="bot" class="w-6 h-6 text-indigo-400"></i>
              </div>
              <div class="min-w-0">
                <div class="font-bold text-lg text-slate-100 tracking-tight">AI SoulMate</div>
                <div class="text-xs text-slate-500 mt-0.5">{{ t('home.footer.brandLegal') }}</div>
              </div>
            </div>
            <h3 class="text-sm font-bold text-slate-100 mb-2">{{ t('home.footer.aboutTitle') }}</h3>
            <p class="text-xs text-slate-400 leading-relaxed">{{ t('home.footer.aboutBody') }}</p>
          </div>

          <!-- 探索 -->
          <div>
            <h3 class="text-sm font-bold text-slate-100 mb-3">{{ t('home.footer.exploreTitle') }}</h3>
            <ul class="space-y-2 text-sm text-slate-400">
              <li>
                <RouterLink to="/studio" class="hover:text-indigo-400 transition">{{ t('home.footer.linkStudio') }}</RouterLink>
              </li>
              <li>
                <RouterLink to="/community" class="hover:text-indigo-400 transition">{{ t('home.footer.linkCommunity') }}</RouterLink>
              </li>
              <li>
                <RouterLink to="/market" class="hover:text-indigo-400 transition">{{ t('home.footer.linkMarket') }}</RouterLink>
              </li>
            </ul>
          </div>

          <!-- 合规 -->
          <div>
            <h3 class="text-sm font-bold text-slate-100 mb-3">{{ t('home.footer.complianceTitle') }}</h3>
            <ul class="space-y-2 text-sm text-slate-400">
              <li>
                <button
                  type="button"
                  class="hover:text-indigo-400 transition text-left w-full sm:w-auto"
                  @click="userAgreementOpen = true"
                >
                  {{ t('home.footer.linkUserAgreement') }}
                </button>
              </li>
            </ul>
          </div>

          <!-- 联系 + 投诉 -->
          <div>
            <h3 class="text-sm font-bold text-slate-100 mb-3">{{ t('home.footer.contactTitle') }}</h3>
            <p class="text-xs text-slate-400 mb-3">{{ t('home.footer.contactHint') }}</p>
            <ul class="space-y-2 text-sm text-slate-400">
              <li class="relative group text-left">
                <span class="cursor-help font-normal hover:text-indigo-400 transition">
                  {{ t('home.complaint.entry') }}
                </span>
                <div
                  class="pointer-events-none absolute bottom-full left-0 z-30 mb-2 hidden w-[min(20rem,calc(100vw-2rem))] rounded-md border border-slate-600 bg-slate-800/95 px-3 py-2 text-left text-[12px] leading-5 text-slate-200 shadow-xl backdrop-blur-sm group-hover:block"
                  role="tooltip"
                >
                  <p class="font-medium text-slate-100">{{ t('home.complaint.hoverTitle') }}</p>
                  <p class="mt-1">{{ t('home.complaint.emailLabel') }}williamsyx@foxmail.com</p>
                  <p>{{ t('home.complaint.phoneLabel') }}13436419828</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 底栏：版权 + 备案 + 快捷链 -->
      <div class="border-t border-white/[0.06] bg-slate-950 px-4 py-3">
        <div
          class="max-w-6xl mx-auto flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between text-[11px] sm:text-xs text-slate-400"
        >
          <p class="text-center sm:text-left">{{ t('home.footer.bottomCopyright') }}</p>
          <div class="flex flex-wrap items-center justify-center sm:justify-end">
            <a
              :href="t('home.footer.icpUrl')"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:text-slate-200 transition"
            >{{ t('home.footer.icpRecord') }}</a>
          </div>
        </div>
      </div>
    </footer>

    <UserAgreementModal v-model="userAgreementOpen" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUpdated } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import UserAgreementModal from '../components/UserAgreementModal.vue'

declare const lucide: any

const { t } = useI18n()
const userAgreementOpen = ref(false)

function renderIcons() {
  if (typeof lucide !== 'undefined' && lucide?.createIcons) {
    lucide.createIcons()
  }
}

onMounted(() => {
  renderIcons()
})

onUpdated(() => {
  renderIcons()
})
</script>

<style scoped>
</style>
