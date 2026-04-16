<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <div class="text-2xl font-bold">{{ t('market.title') }}</div>
        <div class="text-sm text-slate-400 mt-1">{{ t('market.subtitle') }}</div>
      </div>
      <RouterLink to="/checkout" class="btn-primary">{{ t('market.checkout', { count: cart.count }) }}</RouterLink>
    </div>

    <!-- 一行一个商品：列表布局，卡片统一尺寸且自适应宽度 -->
    <div v-if="loading" class="text-center text-slate-400 py-12">
      {{ t('market.loading') }}
    </div>
    <div v-else-if="products.length === 0" class="text-center text-slate-400 py-12">
      {{ t('market.empty') }}
    </div>
    <div v-else class="space-y-6">
      <div
        v-for="p in products"
        :key="p.id"
        class="card flex flex-col md:flex-row gap-6 items-stretch w-full min-h-[240px] cursor-pointer border-2 border-transparent hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-500/20 transition-all duration-300 hover:scale-[1.02]"
        @click="goToDetail(p.id)"
      >
        <div class="w-full md:w-56 h-48 rounded-xl border border-slate-700 bg-slate-900 flex items-center justify-center shrink-0 overflow-hidden">
          <img 
            :src="p.image" 
            :alt="p.name"
            class="w-full h-full object-cover"
            @error="handleImageError"
          />
        </div>
        <div class="flex-1 flex flex-col">
          <!-- 商品名称和价格在同一行 -->
          <div class="flex items-start justify-between gap-4">
            <div class="text-xl font-bold flex-1">{{ p.name }}</div>
            <div class="text-2xl font-bold text-emerald-300 shrink-0">
              <template v-if="p.kind === 'print-pla' || p.kind === 'material-pla'">
                <div class="text-right">
                  <div class="text-2xl font-bold">¥2.00/g</div>
                </div>
              </template>
              <template v-else>¥{{ p.price.toFixed(2) }}</template>
            </div>
          </div>
          
          <div class="text-sm text-slate-400 mt-3 leading-relaxed">{{ p.desc }}</div>
          
          <!-- 商品规格信息展示 -->
          <div class="mt-4 flex-1">
            <div v-if="p.kind === 'print-pla'" class="flex gap-4">
              <!-- 左侧：规格列表 -->
              <div class="w-48 shrink-0 space-y-2">
                <div class="text-xs font-bold text-slate-400 mb-2">{{ t('market.specsAvailable') }}</div>
                <div class="text-sm text-slate-300 space-y-1">
                  <div>{{ t('market.printHeightSpec') }}</div>
                  <div>{{ t('market.materialPlaSpec') }}</div>
                  <div>{{ t('market.pricePerGramSpec') }}</div>
                </div>
              </div>
              
              <!-- 右侧：说明 -->
              <div class="flex-1 rounded-xl border border-slate-700 bg-slate-950/30 p-4">
                <div class="text-xs font-bold text-slate-400 mb-2">{{ t('market.descriptionTitle') }}</div>
                <div class="text-sm text-slate-300 space-y-2">
                  <p>{{ t('market.printDescription') }}</p>
                  <p class="text-slate-500">{{ t('market.printNote') }}</p>
                </div>
              </div>
            </div>

            <div v-else-if="p.kind === 'material-pla'" class="flex gap-4">
              <!-- 左侧：规格列表 -->
              <div class="w-48 shrink-0 space-y-2">
                <div class="text-xs font-bold text-slate-400 mb-2">{{ t('market.specs') }}</div>
                <div class="text-sm text-slate-300 space-y-1">
                  <div>{{ t('market.materialPlaSpec') }}</div>
                  <div>{{ t('market.pricePerGramSpec') }}</div>
                  <div>{{ t('market.packagingSpec') }}</div>
                </div>
              </div>
              
              <!-- 右侧：说明 -->
              <div class="flex-1 rounded-xl border border-slate-700 bg-slate-950/30 p-4">
                <div class="text-xs font-bold text-slate-400 mb-2">{{ t('market.descriptionTitle') }}</div>
                <div class="text-sm text-slate-300 space-y-2">
                  <p>{{ t('market.materialDescription') }}</p>
                  <p class="text-slate-500">{{ t('market.materialColors') }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="msg" class="text-sm" :class="msgType==='error' ? 'text-red-300' : 'text-emerald-300'">{{ formatMsg(msg) }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCartStore } from '../stores/cart'
import { api } from '../lib/api'

const router = useRouter()

const { t } = useI18n()

const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (v.startsWith('market.')) return t(v)
  return v
}

type Product =
  | { id: string; name: string; desc: string; price: number; kind: 'fixed'; image: string }
  | { id: string; name: string; desc: string; price: number; kind: 'print-pla'; image: string }
  | { id: string; name: string; desc: string; price: number; kind: 'material-pla'; image: string }

const cart = useCartStore()
cart.hydrate()

const products = ref<Product[]>([])
const loading = ref(true)

// 从API加载商品数据
onMounted(async () => {
  try {
    const res = await api.products.list({ status_filter: 'active', page_size: 100 })
    products.value = res.items
      .filter((item: any) => {
        // 临时过滤：排除"定制白模"商品（ID: 55555555-5555-5555-5555-555555555555）
        // TODO: 等数据库中删除该商品后，可以移除此过滤逻辑
        return item.id !== '55555555-5555-5555-5555-555555555555'
      })
      .map((item: any) => {
        // 根据price_type判断商品类型
        let kind: 'fixed' | 'print-pla' | 'material-pla' = 'fixed'
        if (item.price_type === 'weight') {
          // 根据分类判断是打印服务还是耗材
          if (item.category_name === 'Print Service') {
            kind = 'print-pla'
          } else if (item.category_name === 'Materials') {
            kind = 'material-pla'
          }
        }
        
        return {
          id: item.id,
          name: item.name,
          desc: item.description || '',
          price: Number(item.price),
          kind,
          image: item.images && item.images.length > 0 ? item.images[0] : 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzFhMjAzMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NDc0OGIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77niYfml6Dms5XliqDovb08L3RleHQ+PC9zdmc+'
        }
      })
      .slice(5)  // 跳过前5个商品
  } catch (err) {
    console.error('Failed to load products:', err)
    msgType.value = 'error'
    msg.value = (err as any)?.message || 'market.loadFailed'
  } finally {
    loading.value = false
  }
})

const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')

function handleImageError(e: Event) {
  const target = e.target as HTMLImageElement
  // 使用base64内联的占位图，避免路径问题
  target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzFhMjAzMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NDc0OGIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77niYfml6Dms5XliqDovb08L3RleHQ+PC9zdmc+'
}

function goToDetail(productId: string) {
  router.push(`/market/${productId}`)
}
</script>

<style scoped>
.card {
  @apply rounded-2xl bg-slate-900/60 backdrop-blur p-6;
}
.btn-primary {
  @apply px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm;
}
.btn-secondary {
  @apply px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm font-bold;
}
</style>
