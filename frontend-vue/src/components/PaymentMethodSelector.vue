<template>
  <div class="space-y-4">
    <!-- 支付方式选择 -->
    <div v-if="!processing">
      <div class="text-sm font-bold text-slate-400 mb-3">{{ t('paymentMethod.chooseTitle') }}</div>
      
      <div v-if="loading" class="text-slate-400 text-sm">{{ t('paymentMethod.loading') }}</div>
      
      <div v-else-if="methods.length === 0" class="text-slate-400 text-sm">
        {{ t('paymentMethod.empty') }}
      </div>
      
      <div v-else class="space-y-3">
        <button
          v-for="method in methods"
          :key="method.id"
          class="w-full p-4 rounded-lg border-2 transition-all duration-300 text-left"
          :class="selectedMethod === method.id 
            ? 'border-indigo-500 bg-indigo-500/10' 
            : 'border-slate-600 bg-slate-800 hover:border-slate-500'"
          type="button"
          @click="selectMethod(method.id)"
        >
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
              <i :data-lucide="method.icon" class="w-5 h-5 text-slate-300"></i>
            </div>
            <div class="flex-1">
              <div class="font-bold text-slate-100 flex items-center gap-2">
                {{ method.name }}
                <span v-if="method.test_mode" class="text-xs px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                  {{ t('paymentMethod.testMode') }}
                </span>
              </div>
              <div class="text-xs text-slate-400 mt-1">{{ method.description }}</div>
            </div>
            <div v-if="selectedMethod === method.id" class="flex-shrink-0">
              <i data-lucide="check-circle" class="w-6 h-6 text-indigo-400"></i>
            </div>
          </div>
        </button>
      </div>

      <!-- 订单金额 -->
      <div class="mt-6 p-4 rounded-lg bg-slate-800 border border-slate-600">
        <div class="flex items-center justify-between mb-2">
          <span class="text-slate-300">{{ t('paymentMethod.orderAmount') }}</span>
          <span class="text-2xl font-bold text-emerald-300">¥{{ amount.toFixed(2) }}</span>
        </div>
        <div v-if="selectedMethod === 'stripe' || selectedMethod === 'paypal'" class="flex items-center justify-between text-sm">
          <span class="text-slate-400">{{ t('paymentMethod.actualUsd') }}</span>
          <span class="text-lg font-bold text-indigo-300">${{ Math.max(amount * 0.14, 0.50).toFixed(2) }}</span>
        </div>
        <div v-if="selectedMethod === 'alipay'" class="flex items-center justify-between text-sm">
          <span class="text-slate-400">{{ t('paymentMethod.actualCny') }}</span>
          <span class="text-lg font-bold text-indigo-300">¥{{ amount.toFixed(2) }}</span>
        </div>
        <div v-if="selectedMethod === 'stripe' || selectedMethod === 'paypal'" class="text-xs text-slate-500 mt-2">
          {{ t('paymentMethod.usdTip') }}
        </div>
        <div v-if="selectedMethod === 'alipay'" class="text-xs text-slate-500 mt-2">
          {{ t('paymentMethod.cnyTip') }}
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-3 mt-6">
        <button
          type="button"
          class="flex-1 px-6 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold"
          @click="$emit('cancel')"
        >
          {{ t('paymentMethod.cancel') }}
        </button>
        <button
          type="button"
          class="flex-1 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-lg shadow-indigo-500/20 disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="!selectedMethod || loading"
          @click="handlePay"
        >
          {{ t('paymentMethod.confirmPay') }}
        </button>
      </div>
    </div>

    <!-- 支付处理中 -->
    <div v-else class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-4 border-slate-600 border-t-indigo-500 mb-4"></div>
      <div class="text-slate-300 font-bold">{{ t(processingMessage) }}</div>
      <div class="text-sm text-slate-400 mt-2">{{ t('paymentMethod.waiting') }}</div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
      {{ formatMsg(error) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../lib/api'

declare const lucide: any

const props = defineProps<{
  amount: number
  orderId: string
}>()

const emit = defineEmits<{
  (e: 'payment-success'): void
  (e: 'payment-error', error: string): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()

const loading = ref(true)
const processing = ref(false)
const processingMessage = ref('paymentMethod.processingPay')
const methods = ref<Array<{ id: string; name: string; description: string; icon: string; test_mode: boolean }>>([])
const selectedMethod = ref('')
const error = ref('')

const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (v.startsWith('paymentMethod.')) return t(v)
  return v
}

async function loadMethods() {
  loading.value = true
  error.value = ''
  try {
    // 传递订单ID，以便获取农场配置的支付方式
    const res = await api.payments.getMethods(props.orderId)
    methods.value = res.methods
    
    // 如果是农场支付，显示提示信息
    if (res.source === 'farm') {
      console.log('使用农场支付配置')
    }
    
    // 默认选中第一个
    if (methods.value.length > 0) {
      selectedMethod.value = methods.value[0].id
    }
    
    // 渲染图标
    setTimeout(() => {
      if (typeof lucide !== 'undefined' && lucide?.createIcons) {
        lucide.createIcons()
      }
    }, 100)
  } catch (e: any) {
    error.value = e?.message || 'paymentMethod.loadFailed'
    console.error('加载支付方式失败:', e)
  } finally {
    loading.value = false
  }
}

function selectMethod(methodId: string) {
  selectedMethod.value = methodId
  error.value = ''
  
  // 重新渲染图标
  setTimeout(() => {
    if (typeof lucide !== 'undefined' && lucide?.createIcons) {
      lucide.createIcons()
    }
  }, 50)
}

async function handlePay() {
  if (!selectedMethod.value) {
    error.value = 'paymentMethod.chooseRequired'
    return
  }

  processing.value = true
  error.value = ''
  processingMessage.value = 'paymentMethod.createPaying'

  try {
    // 根据支付方式选择货币
    let finalAmount = props.amount
    let currency = 'CNY'
    
    if (selectedMethod.value === 'stripe' || selectedMethod.value === 'paypal') {
      // 使用USD货币（测试环境更稳定）
      // 汇率：1 CNY ≈ 0.14 USD
      const amountUSD = props.amount * 0.14
      // Stripe USD最低金额是0.50美元
      finalAmount = Math.max(amountUSD, 0.50)
      currency = 'USD'
    } else if (selectedMethod.value === 'alipay') {
      // 支付宝使用人民币
      finalAmount = props.amount
      currency = 'CNY'
    }
    
    // 获取当前页面的URL作为回调地址
    const currentOrigin = window.location.origin
    
    // 创建支付
    const paymentData = await api.payments.create({
      order_id: props.orderId,
      payment_method: selectedMethod.value,
      amount: finalAmount,
      currency: currency,
      return_url: currentOrigin  // 传递当前域名
    })

    processingMessage.value = 'paymentMethod.redirectingPay'

    // 根据不同的支付方式处理
    if (selectedMethod.value === 'stripe') {
      // Stripe支付 - 跳转到Stripe Checkout
      if (paymentData.checkout_url) {
        window.location.href = paymentData.checkout_url
      } else {
        throw new Error(t('paymentMethod.linkMissing'))
      }
    } else if (selectedMethod.value === 'paypal') {
      // PayPal支付 - 跳转到PayPal
      if (paymentData.approval_url) {
        window.location.href = paymentData.approval_url
      } else {
        throw new Error(t('paymentMethod.linkMissing'))
      }
    } else if (selectedMethod.value === 'alipay') {
      // 支付宝支付 - 跳转到支付宝前，确保token已保存
      if (paymentData.payment_url) {
        // 确保localStorage中的token在跳转前已保存
        // 支付宝跳转是同域跳转，token应该保留，但为了保险再次确认
        const currentToken = localStorage.getItem('auth_token')
        if (currentToken) {
          console.log('支付宝跳转前token已保存')
        }
        
        // 延迟一小段时间确保localStorage写入完成
        await new Promise(resolve => setTimeout(resolve, 100))
        
        window.location.href = paymentData.payment_url
      } else {
        throw new Error(t('paymentMethod.linkMissing'))
      }
    } else {
      throw new Error(t('paymentMethod.unsupported'))
    }
  } catch (e: any) {
    processing.value = false
    error.value = e?.message || 'paymentMethod.payFailed'
    emit('payment-error', formatMsg(error.value))
  }
}

onMounted(() => {
  loadMethods()
})
</script>
