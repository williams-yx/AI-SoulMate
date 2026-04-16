<template>
  <!-- 与登录/注册内用户协议全文弹层一致；挂到 body，z-index 高于登录层 -->
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[10050] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      @click.self="close"
    >
      <div
        class="glass-panel max-w-3xl w-full max-h-[85vh] flex flex-col rounded-2xl border border-slate-700 shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        :aria-label="t('authModal.termsModalTitle')"
        @click.stop
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-700 shrink-0">
          <span class="text-white font-medium text-sm">{{ t('authModal.termsModalTitle') }}</span>
          <button type="button" class="text-slate-400 hover:text-white p-1 rounded-lg" @click="close">
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>
        <div
          class="terms-modal-body-scroll overflow-y-auto px-4 py-4 text-sm text-slate-300 leading-relaxed whitespace-pre-line min-h-0 flex-1 [scrollbar-gutter:stable]"
        >
          {{ t('authModal.termsPlaceholderBody') }}
        </div>
        <div class="border-t border-slate-700 px-4 py-3 shrink-0">
          <button
            type="button"
            class="w-full py-2.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium"
            @click="close"
          >
            {{ t('authModal.termsModalClose') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

declare const lucide: any

const modelValue = defineModel<boolean>({ default: false })

const { t } = useI18n()

function renderIcons() {
  if (typeof lucide !== 'undefined' && lucide?.createIcons) {
    lucide.createIcons()
  }
}

function close() {
  modelValue.value = false
}

watch(modelValue, (v) => {
  if (v) {
    void nextTick(() => {
      setTimeout(renderIcons, 0)
    })
  }
})
</script>

<style scoped>
/* 用户协议弹层：滚动条与深色底融合（轨道透明，滑块低对比） */
.terms-modal-body-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(71 85 105 / 0.45) transparent;
}
.terms-modal-body-scroll::-webkit-scrollbar {
  width: 6px;
}
.terms-modal-body-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.terms-modal-body-scroll::-webkit-scrollbar-thumb {
  background-color: rgb(51 65 85 / 0.5);
  border-radius: 9999px;
  border: 2px solid transparent;
  background-clip: padding-box;
}
.terms-modal-body-scroll::-webkit-scrollbar-thumb:hover {
  background-color: rgb(71 85 105 / 0.65);
}
</style>
