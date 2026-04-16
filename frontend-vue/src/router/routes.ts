import type { RouteRecordRaw } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import LegacyPage from '../views/LegacyPage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import StudioPage from '../views/StudioPage.vue'
import CoursesPage from '../views/CoursesPage.vue'
import CourseDetailPage from '../views/CourseDetailPage.vue'
import WorkflowPage from '../views/WorkflowPage.vue'
import MarketPage from '../views/MarketPage.vue'
import CheckoutPage from '../views/CheckoutPage.vue'
import CommunityPage from '../views/CommunityPage.vue'
import AssetDetailPage from '../views/AssetDetailPage.vue'
import PostDetailPage from '../views/PostDetailPage.vue'
import OrdersPage from '../views/OrdersPage.vue'
import OrderDetailPage from '../views/OrderDetailPage.vue'
import ProductDetailPage from '../views/ProductDetailPage.vue'
import WechatCallbackPage from '../views/WechatCallbackPage.vue'
import RechargeCallbackPage from '../views/RechargeCallbackPage.vue'

import RechargeOrderDetailPage from '../views/RechargeOrderDetailPage.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomePage },
  { path: '/wechat-callback', name: 'wechat-callback', component: WechatCallbackPage },
  { path: '/recharge-callback', name: 'recharge-callback', component: RechargeCallbackPage },
  { path: '/profile', name: 'profile', component: ProfilePage, meta: { requiresAuth: true } },
  { path: '/studio', name: 'studio', component: StudioPage },
  { path: '/courses', name: 'courses', component: CoursesPage },
  { path: '/courses/:id', name: 'course-detail', component: CourseDetailPage, props: true },
  { path: '/workflow', name: 'workflow', component: WorkflowPage },
  { path: '/market', name: 'market', component: MarketPage },
  { path: '/market/:id', name: 'product-detail', component: ProductDetailPage, props: true },
  { path: '/checkout', name: 'checkout', component: CheckoutPage, meta: { requiresAuth: true } },
  { path: '/orders', name: 'orders', component: OrdersPage, meta: { requiresAuth: true } },
  { path: '/orders/:id', name: 'order-detail', component: OrderDetailPage, props: true, meta: { requiresAuth: true } },
  { path: '/recharge-orders/:id', name: 'recharge-order-detail', component: RechargeOrderDetailPage, props: true, meta: { requiresAuth: true } },
  { path: '/community', name: 'community', component: CommunityPage },
  { path: '/community/post/:id', name: 'post-detail', component: PostDetailPage, props: true },
  { path: '/community/:id', name: 'asset-detail', component: AssetDetailPage, props: true },

  // 临时：为了“不丢功能”，先把旧版完整页面嵌进来（后续逐页迁移成 Vue 组件）
  { path: '/legacy', name: 'legacy', component: LegacyPage }
]

