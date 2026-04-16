<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="text-slate-400 hover:text-white">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-2xl font-bold">充值订单详情</h1>
    </div>

    <div v-if="loading" class="panel p-6 text-center text-slate-400">
      加载中...
    </div>

    <div v-else-if="error" class="panel p-6 text-center text-red-400">
      {{ error }}
    </div>

    <div v-else-if="order" class="space-y-6">
      <!-- 订单状态 -->
      <div class="panel p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">订单状态</h2>
          <span
            class="px-4 py-2 rounded-full text-sm font-bold"
            :class="{
              'bg-green-500/20 text-green-300': order.status === 'paid',
              'bg-yellow-500/20 text-yellow-300': order.status === 'pending',
              'bg-red-500/20 text-red-300': order.status === 'failed' || order.status === 'cancelled',
              'bg-purple-500/20 text-purple-300': order.status === 'refunded'
            }"
          >
            {{ getStatusText(order.status) }}
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div class="text-slate-500">订单号</div>
            <div class="mt-1 font-mono">{{ order.id }}</div>
          </div>
          <div>
            <div class="text-slate-500">创建时间</div>
            <div class="mt-1">{{ formatDate(order.created_at) }}</div>
          </div>
          <div v-if="order.paid_at">
            <div class="text-slate-500">支付时间</div>
            <div class="mt-1">{{ formatDate(order.paid_at) }}</div>
          </div>
          <div v-if="order.refunded_at">
            <div class="text-slate-500">退款时间</div>
            <div class="mt-1">{{ formatDate(order.refunded_at) }}</div>
          </div>
        </div>
      </div>

      <!-- 充值信息 -->
      <div class="panel p-6">
        <h2 class="text-xl font-bold mb-4">充值信息</h2>
        
        <div class="space-y-4">
          <div class="flex items-center justify-between py-3 border-b border-slate-700">
            <span class="text-slate-400">支付金额</span>
            <span class="text-2xl font-bold text-emerald-300">¥{{ order.amount_yuan.toFixed(2) }}</span>
          </div>

          <div class="flex items-center justify-between py-3 border-b border-slate-700">
            <span class="text-slate-400">获得积分</span>
            <span class="text-xl font-bold">
              {{ order.amount }}
              <span v-if="order.bonus_amount > 0" class="text-green-400">
                +{{ order.bonus_amount }}
              </span>
              <span class="text-slate-500 text-sm ml-2">
                (共{{ order.total_amount }}积分)
              </span>
            </span>
          </div>

          <div class="flex items-center justify-between py-3 border-b border-slate-700">
            <span class="text-slate-400">积分单价</span>
            <span class="text-lg">¥{{ order.credit_price.toFixed(4) }}/积分</span>
          </div>

          <div class="flex items-center justify-between py-3 border-b border-slate-700">
            <span class="text-slate-400">剩余积分</span>
            <span class="text-lg">
              <span :class="order.remaining_credits > 0 ? 'text-emerald-300' : 'text-slate-500'">
                {{ order.remaining_credits }}
              </span>
              <span class="text-slate-500">/{{ order.total_amount }}</span>
            </span>
          </div>

          <div class="flex items-center justify-between py-3">
            <span class="text-slate-400">支付方式</span>
            <span>{{ getPaymentMethodText(order.payment_method) }}</span>
          </div>

          <div v-if="order.refund_amount" class="flex items-center justify-between py-3 border-t border-slate-700">
            <span class="text-slate-400">退款金额</span>
            <span class="text-xl font-bold text-amber-300">¥{{ order.refund_amount.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- 取消订单按钮（未支付时显示） -->
      <div v-if="order.status === 'pending'" class="panel p-6">
        <h2 class="text-xl font-bold mb-4">订单操作</h2>
        
        <div class="space-y-3">
          <!-- 立即支付按钮 -->
          <button
            @click="handlePay"
            :disabled="paying"
            class="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ paying ? '跳转支付中...' : '立即支付' }}
          </button>

          <!-- 取消订单按钮 -->
          <button
            @click="handleCancel"
            :disabled="cancelling"
            class="w-full py-3 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ cancelling ? '取消中...' : '取消订单' }}
          </button>

          <p v-if="cancelError" class="text-sm text-red-400">{{ cancelError }}</p>
          <p v-if="payError" class="text-sm text-red-400">{{ payError }}</p>
        </div>
      </div>

      <!-- 退款按钮（已支付时显示） -->
      <div v-if="order.status === 'paid' && !order.refunded_at" class="panel p-6">
        <h2 class="text-xl font-bold mb-4">退款申请</h2>
        
        <div v-if="order.can_refund" class="space-y-4">
          <div class="text-sm text-slate-400">
            <p>根据七天无理由退款政策，您可以申请退款。</p>
            <p class="mt-2">
              退款期限：{{ formatDate(order.refund_deadline!) }}
              <span class="text-amber-400 ml-2">(剩余{{ getRemainingDays(order.refund_deadline!) }})</span>
            </p>
            <p v-if="order.remaining_credits < order.total_amount" class="mt-2 text-amber-400">
              您已使用了{{ order.total_amount - order.remaining_credits }}积分，
              将按比例退款¥{{ (order.remaining_credits * order.credit_price).toFixed(2) }}
            </p>
          </div>

          <button
            @click="handleRefund"
            :disabled="refunding"
            class="w-full py-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ refunding ? '退款中...' : '申请退款' }}
          </button>

          <p v-if="refundError" class="text-sm text-red-400">{{ refundError }}</p>
        </div>

        <div v-else class="relative group">
          <button
            disabled
            class="w-full py-3 rounded-lg bg-slate-700 text-slate-500 font-medium cursor-not-allowed"
          >
            已超过退款期限
          </button>
          
          <!-- 悬停提示 -->
          <div class="absolute bottom-full left-0 right-0 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
            <div class="bg-slate-800 border border-slate-600 rounded-lg p-4 shadow-xl text-sm">
              <p class="text-slate-300 mb-1">已超7天的订单，如需退款请联系</p>
              <p class="text-indigo-400">williamsyx@foxmail.com</p>
              <p class="text-indigo-400">13436419828</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 退款说明 -->
      <div class="panel p-6 bg-slate-800/50">
        <h3 class="text-sm font-bold text-slate-300 mb-2">退款说明</h3>
        <ul class="text-xs text-slate-400 space-y-1">
          <li>• 充值后7天内可申请无理由退款</li>
          <li>• 未使用的积分将全额退款</li>
          <li>• 已使用的积分将按比例扣除后退款</li>
          <li>• 退款将原路返回至您的支付账户</li>
          <li>• 退款到账时间：1-7个工作日</li>
          <li>• 早期充值的积分会优先被使用，可能影响退款金额</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '../lib/api'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const order = ref<any>(null)
const refunding = ref(false)
const refundError = ref('')
const cancelling = ref(false)
const cancelError = ref('')
const paying = ref(false)
const payError = ref('')

const orderId = route.params.id as string

onMounted(async () => {
  await loadOrder()
})

async function loadOrder() {
  loading.value = true
  error.value = ''
  
  try {
    const result = await api.credits.getRechargeOrders({ page: 1, page_size: 100 })
    const found = result.orders.find(o => o.id === orderId)
    
    if (found) {
      order.value = found
    } else {
      error.value = '订单不存在'
    }
  } catch (e: any) {
    error.value = e.message || '加载订单失败'
  } finally {
    loading.value = false
  }
}

async function handlePay() {
  if (!order.value) return

  paying.value = true
  payError.value = ''

  try {
    // 重新获取支付链接（使用原订单）
    const result = await api.credits.payRechargeOrder(orderId, window.location.origin)

    if (result.success && result.payment_url) {
      // 跳转到支付页面
      window.location.href = result.payment_url
    } else {
      payError.value = result.message || '获取支付链接失败'
    }
  } catch (e: any) {
    payError.value = e.message || '创建支付失败'
  } finally {
    paying.value = false
  }
}

async function handleCancel() {
  if (!order.value || !confirm('确定要取消此订单吗？')) {
    return
  }

  cancelling.value = true
  cancelError.value = ''

  try {
    const result = await api.credits.cancelRechargeOrder(orderId)
    
    if (result.success) {
      alert('订单已取消')
      await loadOrder() // 重新加载订单
    }
  } catch (e: any) {
    cancelError.value = e.message || '取消订单失败'
  } finally {
    cancelling.value = false
  }
}

async function handleRefund() {
  if (!order.value || !confirm('确定要申请退款吗？退款后积分将被扣除。')) {
    return
  }

  refunding.value = true
  refundError.value = ''

  try {
    const result = await api.credits.refundRechargeOrder(orderId)
    
    if (result.success) {
      alert(`退款成功！退款金额：¥${result.refund_amount.toFixed(2)}，将原路返回至您的支付账户。`)
      await loadOrder() // 重新加载订单
    }
  } catch (e: any) {
    refundError.value = e.message || '退款失败'
  } finally {
    refunding.value = false
  }
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleString('zh-CN')
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    failed: '支付失败',
    cancelled: '已取消',
    refunded: '已退款'
  }
  return map[status] || status
}

function getPaymentMethodText(method: string) {
  const map: Record<string, string> = {
    alipay: '支付宝',
    stripe: 'Stripe',
    paypal: 'PayPal'
  }
  return map[method] || method
}

function getRemainingDays(deadline: string) {
  const d = new Date(deadline)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  
  if (diff <= 0) return '已过期'
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  
  if (days > 0) {
    return `${days}天${hours}小时`
  } else {
    return `${hours}小时`
  }
}
</script>
