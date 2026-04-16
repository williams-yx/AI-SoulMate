<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="text-2xl font-bold">订单详情</div>
      <RouterLink to="/orders" class="btn-secondary">← 返回订单列表</RouterLink>
    </div>

    <div v-if="loading" class="panel p-6 text-slate-400">加载中...</div>
    <div v-else-if="err" class="panel p-6 text-red-300">{{ err }}</div>

    <template v-else-if="order">
      <!-- 订单信息 -->
      <section class="panel p-6">
        <div class="font-bold text-lg mb-4">订单信息</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-slate-400">订单号：</span>
            <span class="text-slate-100">{{ order.id }}</span>
          </div>
          <div>
            <span class="text-slate-400">状态：</span>
            <span :class="statusClass(order.status)">{{ statusText(order.status) }}</span>
          </div>
          <div>
            <span class="text-slate-400">创建时间：</span>
            <span class="text-slate-100">{{ fmt(order.created_at) }}</span>
          </div>
          <div>
            <span class="text-slate-400">更新时间：</span>
            <span class="text-slate-100">{{ fmt(order.updated_at) }}</span>
          </div>
          <div>
            <span class="text-slate-400">支付方式：</span>
            <span class="text-slate-100">{{ order.payment_method || '未设置' }}</span>
          </div>
          <div>
            <span class="text-slate-400">订单金额：</span>
            <span v-if="order.status === 'pricing'" class="text-cyan-300 font-bold text-lg">切片后核价</span>
            <span v-else-if="order.status === 'pricing_failed'" class="text-red-300 font-bold text-lg">核价失败</span>
            <span v-else class="text-emerald-300 font-bold text-lg">¥ {{ Number(order.total_amount).toFixed(2) }}</span>
          </div>
        </div>
      </section>

      <!-- 收货地址 -->
      <section v-if="shippingAddress" class="panel p-6">
        <div class="font-bold text-lg mb-4 flex items-center gap-2">
          <i data-lucide="map-pin" class="w-5 h-5 text-indigo-400"></i>
          收货地址
        </div>
        <div class="bg-slate-950/50 rounded-lg p-4 border border-slate-700 space-y-3">
          <div class="text-sm">
            <span class="text-slate-400">收货人：</span>
            <span class="text-slate-100">{{ shippingAddress.name }}</span>
          </div>
          <div class="text-sm">
            <span class="text-slate-400">联系电话：</span>
            <span class="text-slate-100">{{ shippingAddress.phone }}</span>
          </div>
          <div class="text-sm">
            <span class="text-slate-400">详细地址：</span>
            <span class="text-slate-100">{{ shippingAddress.address }}</span>
          </div>
        </div>
      </section>

      <!-- 订单明细 -->
      <section class="panel p-6">
        <div class="font-bold text-lg mb-4">订单明细</div>
        <div v-if="order.order_items && order.order_items.length > 0" class="space-y-3">
          <div
            v-for="item in order.order_items"
            :key="item.id"
            class="row"
          >
            <div class="flex-1">
              <div class="font-bold text-slate-100">{{ getItemName(item) }}</div>
              <div class="text-xs text-slate-400 mt-1">
                类型：{{ getItemTypeText(item.product_type) }} 
                <span v-if="item.product_id" class="ml-2">商品ID：{{ item.product_id }}</span>
              </div>
              <div v-if="getItemDesc(item)" class="text-xs text-slate-500 mt-1">
                {{ getItemDesc(item) }}
              </div>
              <!-- 打印订单特殊信息 -->
              <div v-if="item.product_type === 'print' && item.specs" class="text-xs text-emerald-400 mt-2 space-y-1">
                <div v-if="getPrintSpecs(item).height">
                  <i data-lucide="ruler" class="w-3 h-3 inline-block mr-1"></i>
                  打印高度：{{ getPrintSpecs(item).height }}
                </div>
                <div v-if="getPrintSpecs(item).material">
                  <i data-lucide="box" class="w-3 h-3 inline-block mr-1"></i>
                  打印材质：{{ getPrintSpecs(item).material }}
                </div>
                <div v-if="getPrintItemWeight(item) !== null">
                  <i data-lucide="weight" class="w-3 h-3 inline-block mr-1"></i>
                  预估克重：{{ formatWeight(getPrintItemWeight(item)) }}g
                </div>
              </div>
            </div>
            <div class="text-right">
              <div class="text-slate-300 text-sm">
                <span v-if="item.product_type === 'print'">
                  ¥{{ Number(item.unit_price).toFixed(2) }}/g × {{ formatWeight(getPrintItemWeight(item) ?? item.quantity) }}g
                </span>
                <span v-else>
                  ¥{{ Number(item.unit_price).toFixed(2) }}/件 × {{ item.quantity }}件
                </span>
              </div>
              <div class="text-emerald-300 font-bold mt-1">
                小计：¥{{ Number(item.total_price).toFixed(2) }}
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-slate-400">暂无订单明细</div>
      </section>

      <!-- 订单进度时间轴（仅打印订单显示） -->
      <section v-if="printJob" class="panel p-6">
        <div class="font-bold text-lg mb-6 flex items-center gap-2">
          <i data-lucide="activity" class="w-5 h-5 text-cyan-400"></i>
          订单进度
        </div>
        <div class="timeline-container">
          <div
            v-for="(step, idx) in timelineSteps"
            :key="step.key"
            class="timeline-step"
          >
            <!-- 连接线（第一个不显示左边线） -->
            <div
              v-if="idx > 0"
              class="timeline-line"
              :class="step.status !== 'pending' ? 'timeline-line-done' : 'timeline-line-pending'"
            ></div>
            <!-- 节点圆点 -->
            <div
              class="timeline-dot"
              :class="[
                step.status === 'done' ? 'timeline-dot-done' : '',
                step.status === 'active' ? 'timeline-dot-active' : '',
                step.status === 'error' ? 'timeline-dot-error' : '',
                step.status === 'pending' ? 'timeline-dot-pending' : '',
              ]"
            >
              <!-- 完成图标 -->
              <svg v-if="step.status === 'done'" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <!-- 活跃脉冲圈 -->
              <span v-else-if="step.status === 'active'" class="timeline-pulse"></span>
              <!-- 错误图标 -->
              <svg v-else-if="step.status === 'error'" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
              <!-- 待处理空心 -->
              <span v-else class="timeline-dot-inner-pending"></span>
            </div>
            <!-- 文字标签 -->
            <div class="timeline-label">
              <span
                class="timeline-title"
                :class="[
                  step.status === 'done' ? 'text-emerald-300' : '',
                  step.status === 'active' ? 'text-cyan-300' : '',
                  step.status === 'error' ? 'text-red-300' : '',
                  step.status === 'pending' ? 'text-slate-500' : '',
                ]"
              >{{ step.label }}</span>
              <span
                v-if="step.desc"
                class="timeline-desc"
                :class="[
                  step.status === 'error' ? 'text-red-400' : 'text-slate-500',
                ]"
              >{{ step.desc }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 打印任务信息（仅打印订单显示） -->
      <section v-if="printJob" class="panel p-6">
        <div class="font-bold text-lg mb-4 flex items-center gap-2">
          <i data-lucide="printer" class="w-5 h-5 text-emerald-400"></i>
          打印任务信息
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 3D模型预览 -->
          <div v-if="printJob.image_url" class="col-span-1">
            <div class="text-xs font-bold text-slate-400 mb-2">3D模型预览</div>
            <img 
              :src="printJob.image_url" 
              class="w-full rounded-lg border border-slate-700 bg-slate-900"
              alt="3D模型预览"
              @error="handleImageError"
            />
          </div>
          
          <!-- 打印信息 -->
          <div class="col-span-1 space-y-3">
            <div>
              <div class="text-xs font-bold text-slate-400 mb-1">打印任务ID</div>
              <div class="text-sm text-slate-200 font-mono">{{ printJob.print_job_id }}</div>
            </div>
            <div>
              <div class="text-xs font-bold text-slate-400 mb-1">打印状态</div>
              <span :class="printStatusClass(printJob.print_status)" class="text-sm font-bold">
                {{ printStatusText(printJob.print_status) }}
              </span>
            </div>
            <div v-if="printJob.shipping_company || printJob.tracking_number">
              <div class="text-xs font-bold text-slate-400 mb-1">物流信息</div>
              <div class="text-sm text-slate-200 space-y-1">
                <div>快递公司：{{ printJob.shipping_company || '-' }}</div>
                <div>快递单号：{{ printJob.tracking_number || '-' }}</div>
              </div>
            </div>
            <div v-if="printJob.print_specs">
              <div class="text-xs font-bold text-slate-400 mb-1">打印规格</div>
              <div class="text-sm text-slate-200 space-y-1">
                <div v-if="getPrintJobSpecs(printJob).height">高度：{{ getPrintJobSpecs(printJob).height }}</div>
                <div v-if="getPrintJobSpecs(printJob).material">材质：{{ getPrintJobSpecs(printJob).material }}</div>
              </div>
            </div>
            <div>
              <div class="text-xs font-bold text-slate-400 mb-1">模型存储桶路径 (STL)</div>
              <div class="text-xs text-slate-300 font-mono break-all">
                {{ getPrintJobSpecs(printJob).model_url || printJob.model_url || '-' }}
              </div>
            </div>
            <div>
              <div class="text-xs font-bold text-slate-400 mb-1">切片存储桶路径 (G-code)</div>
              <div class="text-xs text-slate-300 font-mono break-all">
                {{ printJob.slice_file_key || getPrintJobSpecs(printJob).slice_file_key || '-' }}
              </div>
            </div>
            <div>
              <div class="text-xs font-bold text-slate-400 mb-1">克重信息</div>
              <div class="text-sm text-slate-200 space-y-1">
                <div>预估：{{ formatWeight(getPrintJobWeight(printJob)) }}g</div>
                <div v-if="printJob.actual_weight">
                  实际：{{ Number(printJob.actual_weight).toFixed(0) }}g
                </div>
              </div>
            </div>
            <div v-if="printJob.prompt">
              <div class="text-xs font-bold text-slate-400 mb-1">生成提示词</div>
              <div class="text-sm text-slate-300 italic">{{ printJob.prompt }}</div>
            </div>
            <div v-if="printJob.model_url">
              <a 
                :href="printJob.model_url" 
                target="_blank"
                class="text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <i data-lucide="external-link" class="w-4 h-4"></i>
                查看3D模型文件
              </a>
            </div>
          </div>
        </div>
      </section>

      <!-- 支付方式选择（点击立即支付后显示） -->
      <section v-if="order.status === 'pending' && showPaymentSelector" class="panel p-6 animate-slideDown">
        <div class="font-bold text-lg mb-4">选择支付方式</div>
        <PaymentMethodSelector
          :amount="Number(order.total_amount)"
          :order-id="orderId"
          @payment-success="handlePaymentSuccess"
          @payment-error="handlePaymentError"
          @cancel="showPaymentSelector = false"
        />
      </section>

      <!-- 操作按钮 -->
      <section v-if="['pricing', 'pricing_failed', 'pending', 'paid', 'processing', 'shipped', 'completed'].includes(order.status)" class="panel p-6">
        <div class="flex gap-3 flex-wrap">
          <!-- 立即支付按钮（待支付状态） -->
          <button
            v-if="order.status === 'pending'"
            class="btn-pay"
            style="padding: 1rem 2rem; border-radius: 0.75rem; background-color: rgb(5 150 105); color: white; font-weight: bold; font-size: 1.125rem; border: 2px solid rgb(16 185 129); box-shadow: 0 10px 15px -3px rgb(16 185 129 / 0.2); transition: all 0.3s;"
            type="button"
            :disabled="busy"
            @click="showPaymentSelector = !showPaymentSelector"
          >
            {{ showPaymentSelector ? '收起支付' : '立即支付' }}
          </button>
          
          <!-- 确认收货按钮（已发货状态） -->
          <button
            v-if="order.status === 'shipped'"
            class="btn-confirm-receipt"
            style="padding: 1rem 2rem; border-radius: 0.75rem; background-color: rgb(34 211 238); color: rgb(15 23 42); font-weight: bold; font-size: 1.125rem; border: 2px solid rgb(6 182 212); box-shadow: 0 10px 15px -3px rgb(6 182 212 / 0.3); transition: all 0.3s;"
            type="button"
            :disabled="busy"
            @click="handleConfirmReceipt"
          >
            {{ busy ? '处理中...' : '确认收货' }}
          </button>

          <!-- 取消订单按钮（支付前） -->
          <button
            v-if="['pricing', 'pricing_failed', 'pending'].includes(order.status)"
            class="btn-cancel"
            style="padding: 1rem 2rem; border-radius: 0.75rem; background-color: rgb(30 41 59); color: rgb(226 232 240); font-weight: bold; font-size: 1.125rem; border: 2px solid rgb(71 85 105); transition: all 0.3s;"
            type="button"
            :disabled="busy"
            @click="handleCancel"
          >
            {{ busy ? '处理中...' : '取消订单' }}
          </button>

          <!-- 申请退货按钮（支付后） -->
          <button
            v-if="['paid', 'processing', 'shipped', 'completed'].includes(order.status)"
            class="btn-refund"
            style="padding: 1rem 2rem; border-radius: 0.75rem; background-color: rgb(251 146 60); color: white; font-weight: bold; font-size: 1.125rem; border: 2px solid rgb(249 115 22); box-shadow: 0 10px 15px -3px rgb(249 115 22 / 0.2); transition: all 0.3s;"
            type="button"
            @click="handleRefundRequest"
          >
            申请退货
          </button>
        </div>
      </section>
    </template>

    <div v-if="msg" class="text-sm" :class="msgType==='error' ? 'text-red-300' : 'text-emerald-300'">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'
import PaymentMethodSelector from '../components/PaymentMethodSelector.vue'

const route = useRoute()
const router = useRouter()
const orderId = route.params.id as string

const loading = ref(true)
const err = ref('')
const order = ref<any>(null)
const printJob = ref<any>(null)
const busy = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')
const showPaymentSelector = ref(false)
// 收货地址信息
const shippingAddress = ref<any>(null)

declare const lucide: any

function fmt(s: string) {
  if (!s) return '--'
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString()
}

function statusText(status: string) {
  const map: Record<string, string> = {
    pricing: '切片定价中',
    pricing_failed: '切片定价失败',
    pending: '待支付',
    awaiting_payment: '待支付',
    paid: '已支付',
    processing: '打印处理中',
    shipped: '已发货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return map[status] || status
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    pricing: 'text-cyan-300',
    pricing_failed: 'text-red-300',
    pending: 'text-yellow-300',
    awaiting_payment: 'text-yellow-300',
    paid: 'text-emerald-300',
    processing: 'text-cyan-300',
    shipped: 'text-blue-300',
    completed: 'text-slate-300',
    cancelled: 'text-red-300',
  }
  return map[status] || 'text-slate-300'
}

function getItemName(item: any) {
  try {
    const snapshot = typeof item.product_snapshot === 'string' 
      ? JSON.parse(item.product_snapshot) 
      : item.product_snapshot
    return snapshot?.name || 'Unknown Product'
  } catch {
    return 'Unknown Product'
  }
}

function getItemDesc(item: any) {
  try {
    const snapshot = typeof item.product_snapshot === 'string' 
      ? JSON.parse(item.product_snapshot) 
      : item.product_snapshot
    return snapshot?.description || ''
  } catch {
    return ''
  }
}

function getItemTypeText(type: string) {
  const map: Record<string, string> = {
    product: '商品',
    print: '打印服务',
    course: '课程',
    custom: '自定义',
  }
  return map[type] || type
}

function getPrintSpecs(item: any) {
  try {
    const specs = typeof item.specs === 'string' ? JSON.parse(item.specs) : item.specs
    return specs || {}
  } catch {
    return {}
  }
}

function getPrintJobSpecs(job: any) {
  try {
    const specs = typeof job.print_specs === 'string' ? JSON.parse(job.print_specs) : job.print_specs
    return specs || {}
  } catch {
    return {}
  }
}

function normalizeWeight(value: any): number | null {
  const num = Number(value)
  if (!Number.isFinite(num) || num <= 0) return null
  return num
}

function formatWeight(value: any) {
  const num = normalizeWeight(value)
  if (num === null) return '--'
  return Number.isInteger(num) ? num.toFixed(0) : num.toFixed(2)
}

function getPrintItemWeight(item: any): number | null {
  const specs = getPrintSpecs(item)
  return normalizeWeight(specs.slicer_estimated_weight ?? specs.estimated_weight)
}

function getPrintJobWeight(job: any): number | null {
  const specs = getPrintJobSpecs(job)
  return normalizeWeight(job?.estimated_weight ?? specs.slicer_estimated_weight ?? specs.estimated_weight)
}

function printStatusText(status: string) {
  const map: Record<string, string> = {
    queued: '排队中',
    slicing: '切片中',
    awaiting_payment: '待支付',
    pending: '等待打印',
    claimed: '已领取',
    downloading: '下载中',
    printing: '打印中',
    completed: '打印完成',
    complete: '打印完成',
    cooling: '冷却中',
    finished: '已完成',
    received: '用户已签收',
    failed: '打印失败',
  }
  return map[status] || status
}

function printStatusClass(status: string) {
  const map: Record<string, string> = {
    queued: 'text-yellow-300',
    slicing: 'text-blue-300',
    awaiting_payment: 'text-cyan-300',
    pending: 'text-yellow-300',
    claimed: 'text-indigo-300',
    downloading: 'text-indigo-300',
    printing: 'text-blue-300',
    completed: 'text-emerald-300',
    complete: 'text-emerald-300',
    cooling: 'text-cyan-300',
    finished: 'text-emerald-300',
    received: 'text-emerald-300',
    failed: 'text-red-300',
  }
  return map[status] || 'text-slate-300'
}

type TimelineStep = {
  key: string
  label: string
  desc: string
  status: 'done' | 'active' | 'error' | 'pending'
}



const timelineSteps = computed<TimelineStep[]>(() => {
  const orderStatus = (order.value?.status || '').toLowerCase()
  const pj = printJob.value
  const printStatus = (pj?.print_status || '').toLowerCase()
  const sliceStatus = (pj?.slice_status || '').toLowerCase()
  const shippingCompany = pj?.shipping_company || ''
  const trackingNumber = pj?.tracking_number || ''

  const isCancelled = orderStatus === 'cancelled'
  const pricingFailed = orderStatus === 'pricing_failed' || sliceStatus === 'failed'
  const pricingDone = ['pending', 'paid', 'processing', 'shipped', 'completed'].includes(orderStatus)
  const isPaid = ['paid', 'processing', 'shipped', 'completed'].includes(orderStatus)
  const sliceReady = sliceStatus === 'ready'
  const sliceFailed = sliceStatus === 'failed'
  const assigned = !!(
    (isPaid && pj?.claimed_by_client_id)
    || (isPaid && pj?.farm_assignment)
    || (isPaid && pj?.target_client_id)
    || (isPaid && printStatus === 'pending')
  )
  const printingActive = ['claimed', 'downloading', 'printing', 'cooling', 'completed', 'complete', 'finished', 'shipped', 'received'].includes(printStatus)
    || ['processing', 'shipped', 'completed'].includes(orderStatus)
  const shippedDone = ['shipped', 'completed'].includes(orderStatus) || printStatus === 'shipped'
  const receivedDone = orderStatus === 'completed' || printStatus === 'received'

  const steps: TimelineStep[] = [
    {
      key: 'created',
      label: '创建订单',
      desc: order.value?.created_at ? fmt(order.value.created_at) : '',
      status: 'done',
    },
    {
      key: 'slice',
      label: '切片处理',
      desc: sliceReady ? '已生成 G-code 并解析克重' : (sliceFailed ? '切片失败' : '正在真实切片并解析克重'),
      status: sliceReady ? 'done' : ((sliceFailed || pricingFailed) ? 'error' : 'active'),
    },
    {
      key: 'priced',
      label: '核算金额',
      desc: pricingFailed
        ? '克重解析失败，暂不可支付'
        : (pricingDone ? `已核算金额${order.value?.total_amount != null ? ` ¥${Number(order.value.total_amount).toFixed(2)}` : ''}` : '等待切片完成后核价'),
      status: pricingDone ? 'done' : (pricingFailed ? 'error' : (sliceReady ? 'active' : 'pending')),
    },
    {
      key: 'paid',
      label: isCancelled ? '订单已取消' : (isPaid ? '支付成功' : '待支付'),
      desc: isCancelled
        ? '订单已取消'
        : (isPaid ? '支付完成，准备分配打印节点' : (pricingDone ? '金额已确认，可立即支付' : '需先完成切片核价')),
      status: isCancelled ? 'error' : (isPaid ? 'done' : (pricingDone ? 'active' : 'pending')),
    },
    {
      key: 'assign',
      label: '分配打印节点',
      desc: assigned ? (pj?.farm_assignment?.farm_name || pj?.claimed_by_client_id || pj?.target_client_id || '已分配，待打印') : '支付完成后分配打印节点',
      status: assigned ? 'done' : (isPaid ? 'active' : 'pending'),
    },
    {
      key: 'printing',
      label: '正在打印',
      desc: printingActive
        ? (pj?.started_at ? `开始于 ${fmt(pj.started_at)}` : '打印机已确认开始')
        : '等待打印机确认开始',
      status: receivedDone || shippedDone ? 'done' : (printingActive ? 'active' : 'pending'),
    },
    {
      key: 'shipping',
      label: '已发货',
      desc: shippedDone
        ? `${shippingCompany || '快递公司待更新'}${trackingNumber ? ` · ${trackingNumber}` : ''}`
        : '商家待填写快递公司与单号',
      status: receivedDone ? 'done' : (shippedDone ? 'active' : 'pending'),
    },
    {
      key: 'received',
      label: '已收货',
      desc: receivedDone ? (pj?.received_at ? `签收于 ${fmt(pj.received_at)}` : '用户已确认收货') : '等待用户确认收货',
      status: receivedDone ? 'done' : 'pending',
    },
  ]

  return steps
})

async function handleConfirmReceipt() {
  if (busy.value) return
  if (!confirm('确定已收到包裹并确认收货吗？')) return
  
  busy.value = true
  try {
    await api.orders.confirmReceipt(orderId)
    toastOk('订单已完成，感谢支持！')
    await loadOrder()
  } catch (e: any) {
    toastErr(e?.message || '确认收货失败')
  } finally {
    busy.value = false
  }
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  console.error('图片加载失败:', img.src)
  // 可以设置一个默认图片
  // img.src = '/placeholder.png'
}

function toastOk(t: string) {
  msgType.value = 'ok'
  msg.value = t
  setTimeout(() => (msg.value = ''), 2000)
}

function toastErr(t: string) {
  msgType.value = 'error'
  msg.value = t
  setTimeout(() => (msg.value = ''), 2600)
}

async function loadOrder() {
  loading.value = true
  err.value = ''
  try {
    order.value = await api.orders.detail(orderId)
    
    // 解析收货地址
    if (order.value.shipping_address) {
      try {
        shippingAddress.value = typeof order.value.shipping_address === 'string'
          ? JSON.parse(order.value.shipping_address)
          : order.value.shipping_address
      } catch (e) {
        console.error('Failed to parse shipping address:', e)
      }
    }
    
    // 检查是否为打印订单，如果是则加载打印任务信息
    const hasPrintItem = order.value.order_items?.some((item: any) => item.product_type === 'print')
    if (hasPrintItem) {
      try {
        printJob.value = await api.printOrders.getPrintJob(orderId)
      } catch (e) {
        console.error('Failed to load print job:', e)
      }
    }
    
    // 渲染图标
    setTimeout(() => {
      if (typeof lucide !== 'undefined' && lucide?.createIcons) {
        lucide.createIcons()
      }
    }, 100)
  } catch (e: any) {
    err.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function handlePaymentSuccess() {
  showPaymentSelector.value = false
  toastOk('支付成功！')
  loadOrder()
}

function handlePaymentError(error: string) {
  toastErr(error || '支付失败')
}

async function handleCancel() {
  if (busy.value) return
  if (!confirm('确定要取消订单吗？')) return
  
  busy.value = true
  try {
    await api.orders.cancel(orderId)
    toastOk('订单已取消')
    await loadOrder()
  } catch (e: any) {
    toastErr(e?.message || '取消失败')
  } finally {
    busy.value = false
  }
}

function handleRefundRequest() {
  alert('退货请联系\nwilliamsyx@foxmail.com\n13436419828')
}

onMounted(async () => {
  // 先检查是否从支付页面返回
  const paymentStatus = route.query.payment as string
  
  if (paymentStatus === 'success') {
    console.log('检测到支付成功返回，开始确认支付...')
    // 支付成功，需要确认支付
    await handlePaymentReturn()
  } else if (paymentStatus === 'cancel') {
    toastErr('支付已取消')
    // 清除URL参数
    router.replace({ path: `/orders/${orderId}` })
  }
  
  // 然后加载订单
  await loadOrder()
})

async function handlePaymentReturn() {
  console.log('handlePaymentReturn 开始执行')
  try {
    toastOk('正在确认支付状态...')
    
    // 先加载订单获取payment_id
    console.log('加载订单信息...')
    await loadOrder()
    
    if (!order.value) {
      console.error('订单信息加载失败')
      toastErr('订单信息加载失败')
      return
    }
    
    console.log('订单信息:', order.value)
    
    // 从订单中获取payment_id（后端在创建支付时已保存）
    const paymentId = order.value.payment_id
    const paymentMethod = order.value.payment_method
    
    console.log('payment_id:', paymentId, 'payment_method:', paymentMethod)
    
    if (!paymentId || !paymentMethod) {
      console.error('支付信息不完整')
      toastErr('支付信息不完整，请联系客服')
      router.replace({ path: `/orders/${orderId}` })
      return
    }
    
    // 调用后端确认支付
    console.log('调用确认支付API...')
    await api.payments.confirm({
      order_id: orderId,
      payment_method: paymentMethod,
      payment_id: paymentId
    })
    
    console.log('支付确认成功')
    toastOk('支付确认成功！')
    // 清除URL参数并重新加载订单
    router.replace({ path: `/orders/${orderId}` })
    await loadOrder()
  } catch (e: any) {
    console.error('支付确认失败:', e)
    toastErr(e?.message || '支付确认失败')
    // 即使失败也清除URL参数
    router.replace({ path: `/orders/${orderId}` })
  }
}
</script>

<style scoped>
.panel {
  @apply rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur;
}
.btn-primary {
  @apply px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-lg shadow-indigo-500/20 disabled:opacity-60 disabled:cursor-not-allowed;
}
.btn-secondary {
  @apply px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm font-bold disabled:opacity-60 disabled:cursor-not-allowed;
}
.btn-pay {
  @apply px-8 py-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-lg border-4 border-yellow-400 shadow-lg shadow-emerald-500/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all;
}
.btn-cancel {
  @apply px-8 py-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-lg border-4 border-red-500 disabled:opacity-60 disabled:cursor-not-allowed transition-all;
}
.row {
  @apply flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-950/30 border border-slate-700;
}

/* ===== 订单进度时间轴 ===== */
.timeline-container {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  position: relative;
  padding: 0 0.5rem;
}

.timeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
  min-width: 0;
}

/* 连接线 */
.timeline-line {
  position: absolute;
  top: 18px;
  right: 50%;
  width: 100%;
  height: 3px;
  z-index: 0;
  border-radius: 2px;
}
.timeline-line-done {
  background: linear-gradient(90deg, #34d399, #22d3ee);
}
.timeline-line-pending {
  background: rgba(100, 116, 139, 0.3);
}

/* 圆点 */
.timeline-dot {
  position: relative;
  z-index: 1;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.timeline-dot-done {
  background: linear-gradient(135deg, #059669, #10b981);
  color: white;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
}

.timeline-dot-active {
  background: linear-gradient(135deg, #0891b2, #22d3ee);
  color: white;
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.5);
  animation: dotGlow 2s ease-in-out infinite;
}

.timeline-dot-error {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: white;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
}

.timeline-dot-pending {
  background: rgba(51, 65, 85, 0.6);
  border: 2px solid rgba(100, 116, 139, 0.4);
}

.timeline-dot-inner-pending {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(100, 116, 139, 0.5);
}

/* 脉冲动画 */
.timeline-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
  position: relative;
}
.timeline-pulse::before {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.6);
  animation: pulseRing 1.5s ease-out infinite;
}

/* 标签文字 */
.timeline-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 10px;
  text-align: center;
  min-width: 0;
  width: 100%;
}

.timeline-title {
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
}

.timeline-desc {
  font-size: 0.65rem;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

@keyframes pulseRing {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

@keyframes dotGlow {
  0%, 100% {
    box-shadow: 0 0 16px rgba(34, 211, 238, 0.5);
  }
  50% {
    box-shadow: 0 0 24px rgba(34, 211, 238, 0.8);
  }
}

/* 响应式：小屏时竖直排列 */
@media (max-width: 640px) {
  .timeline-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 0;
    padding: 0;
  }
  .timeline-step {
    flex-direction: row;
    align-items: center;
    width: 100%;
    padding-left: 0;
  }
  .timeline-line {
    position: absolute;
    top: auto;
    right: auto;
    left: 17px;
    bottom: 100%;
    width: 3px;
    height: 28px;
  }
  .timeline-label {
    align-items: flex-start;
    margin-top: 0;
    margin-left: 14px;
    text-align: left;
    padding: 10px 0;
  }
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(100%);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.2s ease-out;
}

.animate-slideUp {
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.animate-slideDown {
  animation: slideDown 0.3s ease-out;
}
</style>
