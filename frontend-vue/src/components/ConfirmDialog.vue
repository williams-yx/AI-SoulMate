<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
    @click.self="handleCancel"
  >
    <div class="glass-panel max-w-md w-full mx-auto rounded-2xl p-6 border border-slate-700 shadow-2xl">
      <!-- 标题 -->
      <h3 class="text-lg font-bold text-white mb-2">{{ resolvedTitle }}</h3>
      
      <!-- 内容 -->
      <p class="text-slate-300 mb-6">{{ message }}</p>
      
      <!-- 按钮组 -->
      <div class="flex items-center justify-end gap-3">
        <button
          v-if="!singleButton"
          class="btn-cancel"
          type="button"
          @click="handleCancel"
        >
          {{ resolvedCancelText }}
        </button>
        <button
          :class="singleButton ? 'btn-confirm btn-confirm-primary' : 'btn-confirm'"
          type="button"
          @click="handleConfirm"
        >
          {{ resolvedConfirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    message: string
    confirmText?: string
    cancelText?: string
    /** 仅显示确认按钮（用于成功提示等） */
    singleButton?: boolean
  }>(),
  {
    title: '确认',
    confirmText: '确认',
    cancelText: '取消',
    singleButton: false,
  }
)

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
  (e: 'update:open', value: boolean): void
}>()

const { t } = useI18n()

const resolvedTitle = computed(() => props.title || t('confirmDialog.title'))
const resolvedConfirmText = computed(() => props.confirmText || t('confirmDialog.confirm'))
const resolvedCancelText = computed(() => props.cancelText || t('confirmDialog.cancel'))

function handleConfirm() {
  emit('confirm')
  emit('update:open', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}

// 监听 ESC 键关闭
let escHandler: ((e: KeyboardEvent) => void) | null = null

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      escHandler = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          handleCancel()
        }
      }
      document.addEventListener('keydown', escHandler)
    } else {
      if (escHandler) {
        document.removeEventListener('keydown', escHandler)
        escHandler = null
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.btn-cancel {
  @apply px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm font-medium transition shadow-sm hover:shadow-md;
}

.btn-confirm {
  @apply px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition shadow-sm hover:shadow-md shadow-red-500/20;
}

.btn-confirm-primary {
  @apply bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20;
}
</style>
