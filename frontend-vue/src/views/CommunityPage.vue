<template>
  <div class="community-container">
    <LoginPromptModal
      v-model:open="loginPromptOpen"
      :message="t(loginPromptMessage)"
      @goLogin="loginPromptOpen = false"
    />

    <div class="community-header">
      <h1 class="community-title">{{ t('community.title') }}</h1>
      <div class="community-controls">
        <button class="community-publish-btn community-btn-fixed" type="button" @click="openPublishModal">
          {{ t('community.publishPost') }}
        </button>
        <select v-model="sort" class="community-sort-select" @change="load">
          <option value="hot">{{ t('community.sortHot') }}</option>
          <option value="popular">{{ t('community.sortPopular') }}</option>
          <option value="new">{{ t('community.sortNew') }}</option>
        </select>
        <button class="community-refresh-btn community-btn-fixed" type="button" @click="load">
          {{ t('community.refresh') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="community-loading">{{ t('community.loading') }}</div>
    <div v-else-if="error" class="community-error">{{ errorDisplay }}</div>

    <div v-else class="community-grid">
      <template v-for="item in items" :key="`${item.item_type}-${item.id}`">
        <RouterLink
          v-if="item.item_type === 'asset'"
          class="asset-card"
          :to="`/community/${item.id}`"
        >
        <div class="asset-card-image-wrapper">
          <img :src="resolveMediaUrl(item.image_url)" class="asset-card-image" :alt="item.prompt" @error="(e) => handlePreviewError(item, e)" />
          <div v-if="item.tags?.length" class="asset-card-tag">
            {{ item.tags[0] }}
          </div>
        </div>
        <div class="asset-card-content">
          <h3 class="asset-card-title">{{ item.prompt }}</h3>
          <p class="asset-card-author">{{ t('community.authorPrefix') }}{{ item.author_name }}</p>
          <div class="asset-card-stats">
            <div class="asset-stat-item">
              <svg class="asset-stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>{{ item.stats?.downloads || 0 }}</span>
            </div>
            <button
              class="asset-stat-item asset-stat-like"
              type="button"
              :class="{ 'asset-stat-like-active': isLiked(item) }"
              @click.stop.prevent="toggleLike(item)"
            >
              <svg class="asset-stat-icon" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
              </svg>
              <span>{{ item.stats?.likes || 0 }}</span>
            </button>
          </div>
        </div>
        </RouterLink>

        <RouterLink v-else class="post-card" :to="`/community/post/${item.id}`">
          <div class="post-card-head">
            <div class="post-card-author">{{ item.author_name }}</div>
            <div class="post-card-time">{{ formatTime(item.created_at) }}</div>
          </div>
          <div class="post-preview-box" :class="`post-preview-box-${getPostPreview(item).kind}`">
            <div class="post-preview-meta">{{ getPostPreviewLabel(item) }}</div>
            <div class="post-preview-body">
              <div v-if="getPostPreview(item).kind === 'model'" class="post-model-preview">
                <div class="post-model-badge">3D</div>
                <div class="post-model-name">{{ getPostModelName(item) }}</div>
                <a
                  class="post-file-link"
                  :href="resolveMediaUrl(getPostPreview(item).url)"
                  target="_blank"
                  rel="noreferrer"
                  @click.stop
                >
                  {{ t('community.open3dFile') }}
                </a>
              </div>
              <img
                v-else-if="getPostPreview(item).kind === 'image'"
                class="post-media-image"
                :src="resolveMediaUrl(getPostPreview(item).url)"
                alt="post image"
              />
              <p
                v-else
                class="post-text-preview"
                :class="getPostTextSizeClass(item)"
              >
                {{ item.content?.trim() || t('community.emptyPostContent') }}
              </p>
            </div>
          </div>

          <p
            v-if="getPostPreview(item).kind !== 'text' && item.content"
            class="post-card-content post-card-content-compact"
          >
            {{ item.content }}
          </p>

          <div class="post-hidden-meta" v-if="getPostHiddenMediaCount(item) > 0">
            {{ t('community.moreMediaInDetail') }}
          </div>

          <div v-if="item.models?.length" class="post-file-list compact">
            <span class="post-file-pill">{{ t('community.modelCount', { count: item.models.length }) }}</span>
          </div>

          <div v-if="item.images?.length" class="post-file-list compact">
            <span class="post-file-pill">{{ t('community.imageCount', { count: item.images.length }) }}</span>
          </div>

          <div v-if="item.videos?.length" class="post-file-list compact">
            <span class="post-file-pill">{{ t('community.videoCount', { count: item.videos.length }) }}</span>
          </div>

          <div class="post-card-actions">
            <button
              class="asset-stat-item asset-stat-like"
              type="button"
              :class="{ 'asset-stat-like-active': isLiked(item) }"
              @click.stop.prevent="toggleLike(item)"
            >
              <svg class="asset-stat-icon" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
              </svg>
              <span>{{ item.stats?.likes || 0 }}</span>
            </button>
          </div>
        </RouterLink>
      </template>
    </div>

    <div v-if="publishOpen" class="publish-overlay" @click.self="closePublishModal">
      <div class="publish-dialog">
        <div class="publish-header">
          <h2 class="publish-title">{{ t('community.publishTitle') }}</h2>
          <button class="publish-close" type="button" @click="closePublishModal">×</button>
        </div>

        <textarea
          v-model="postContent"
          class="publish-textarea"
          :placeholder="t('community.publishPlaceholder')"
          maxlength="10000"
        ></textarea>

        <div class="publish-upload-block">
          <label class="publish-label">{{ t('community.uploadImages') }}</label>
          <input
            ref="publishImageInput"
            type="file"
            accept="image/*"
            multiple
            class="publish-file-input-hidden"
            @change="onImageSelect"
          />
          <button class="btn-image-select community-btn-fixed" type="button" @click="triggerPublishImageInput">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            {{ t('community.selectPhotos') }}
          </button>
          <div v-if="imageFiles.length" class="publish-file-list">
            <div v-for="(file, idx) in imageFiles" :key="`img-${idx}`" class="publish-file-item">
              <span>{{ file.name }}</span>
              <button type="button" @click="removeImage(idx)">{{ t('community.remove') }}</button>
            </div>
          </div>
        </div>

        <div class="publish-upload-block">
          <label class="publish-label">{{ t('community.uploadModels') }}</label>
          <input
            ref="publishModelInput"
            type="file"
            accept=".glb,.gltf,.obj,.stl,.fbx"
            multiple
            class="publish-file-input-hidden"
            @change="onModelSelect"
          />
          <button class="btn-image-select community-btn-fixed" type="button" @click="triggerPublishModelInput">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20h10M7 4h10M5 8l2 4-2 4h14l-2-4 2-4H5z" />
            </svg>
            {{ t('community.select3dFiles') }}
          </button>
          <div v-if="modelFiles.length" class="publish-file-list">
            <div v-for="(file, idx) in modelFiles" :key="`model-${idx}`" class="publish-file-item">
              <span>{{ file.name }}</span>
              <button type="button" @click="removeModel(idx)">{{ t('community.remove') }}</button>
            </div>
          </div>
        </div>

        <div class="publish-upload-block">
          <label class="publish-label">{{ t('community.uploadVideos') }}</label>
          <input
            ref="publishVideoInput"
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            multiple
            class="publish-file-input-hidden"
            @change="onVideoSelect"
          />
          <button class="btn-image-select community-btn-fixed" type="button" @click="triggerPublishVideoInput">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
            </svg>
            {{ t('community.selectVideos') }}
          </button>
          <div v-if="videoFiles.length" class="publish-file-list">
            <div v-for="(file, idx) in videoFiles" :key="`video-${idx}`" class="publish-file-item">
              <span>{{ file.name }}</span>
              <button type="button" @click="removeVideo(idx)">{{ t('community.remove') }}</button>
            </div>
          </div>
        </div>

        <p v-if="publishStatus" class="publish-status">{{ publishStatusDisplay }}</p>

        <div class="publish-actions">
          <button class="community-refresh-btn community-btn-fixed" type="button" @click="closePublishModal" :disabled="publishing">
            {{ t('community.cancel') }}
          </button>
          <button class="community-publish-btn community-btn-fixed" type="button" @click="submitPost" :disabled="publishing">
            {{ publishing ? t('community.publishing') : t('community.confirmingPublish') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { api, resolveMediaUrl } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import LoginPromptModal from '../components/LoginPromptModal.vue'

type AssetItem = {
  item_type: 'asset'
  id: string
  image_url: string
  prompt: string
  base_model: string
  tags: string[]
  stats: { likes: number; downloads: number }
  author_name: string
  author_id?: string
  liked_by_me?: boolean
  _preview_refreshed_once?: boolean
}

type PostItem = {
  item_type: 'post'
  id: string
  content: string
  images: string[]
  models: string[]
  videos: string[]
  stats: { likes: number }
  author_name: string
  author_id?: string
  created_at?: string | null
  liked_by_me?: boolean
}

type CommunityItem = AssetItem | PostItem

type SortType = 'hot' | 'new' | 'popular'

const loading = ref(false)
const error = ref('')
const items = ref<CommunityItem[]>([])
const sort = ref<SortType>('hot')
const auth = useAuthStore()
const { t, locale } = useI18n()
const loginPromptOpen = ref(false)
const loginPromptMessage = ref('community.loginRequiredAction')
const publishOpen = ref(false)
const publishing = ref(false)
const publishStatus = ref('')
const publishStatusDisplay = computed(() => {
  const v = publishStatus.value
  return typeof v === 'string' && v.startsWith('community.') ? t(v) : v
})

// 临时屏蔽的社区条目 ID（注：仅在列表中隐藏，详情页仍可直接访问）
const BLOCKED_COMMUNITY_IDS = new Set([
  'b34e775f-1a10-4489-8840-c31414cb72a3',
  '2c5f1e6a-40a8-430e-9288-89923f64cc91'
])
const errorDisplay = computed(() => {
  const v = error.value
  return typeof v === 'string' && v.startsWith('community.') ? t(v) : v
})
const postContent = ref('')
const imageFiles = ref<File[]>([])
const modelFiles = ref<File[]>([])
const videoFiles = ref<File[]>([])
const publishImageInput = ref<HTMLInputElement | null>(null)
const publishModelInput = ref<HTMLInputElement | null>(null)
const publishVideoInput = ref<HTMLInputElement | null>(null)
auth.hydrate()

function isLiked(item: CommunityItem) {
  return !!item.liked_by_me
}

function formatTime(raw?: string | null) {
  if (!raw) return t('community.justNow')
  const time = new Date(raw)
  if (Number.isNaN(time.getTime())) return t('community.justNow')
  return time.toLocaleString(locale.value, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function normalizeMediaUrl(value: unknown): string {
  if (typeof value !== 'string') return ''
  const trimmed = value.trim()
  return trimmed
}

function normalizeStringArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((v) => normalizeMediaUrl(v)).filter(Boolean)
  }

  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return []

    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) {
        return parsed.map((v) => normalizeMediaUrl(v)).filter(Boolean)
      }
    } catch {
      // 非 JSON 字符串时，当作单个值处理
    }

    const single = normalizeMediaUrl(trimmed)
    return single ? [single] : []
  }

  return []
}

function normalizeCommunityItem(item: any): CommunityItem {
  if (item?.item_type === 'post') {
    return {
      ...item,
      images: normalizeStringArray(item.images),
      models: normalizeStringArray(item.models),
      videos: normalizeStringArray(item.videos),
    } as PostItem
  }

  return {
    ...item,
    tags: normalizeStringArray(item?.tags),
  } as AssetItem
}

function getPostPreview(post: PostItem): { kind: 'model' | 'image' | 'text'; url: string } {
  const modelUrl = (post.models || []).map((u) => normalizeMediaUrl(u)).find((u) => !!u)
  if (modelUrl) {
    return { kind: 'model', url: modelUrl }
  }

  const imageUrl = (post.images || []).map((u) => normalizeMediaUrl(u)).find((u) => !!u)
  if (imageUrl) {
    return { kind: 'image', url: imageUrl }
  }

  return { kind: 'text', url: '' }
}

function getPostPreviewLabel(post: PostItem) {
  const preview = getPostPreview(post)
  if (preview.kind === 'model') return t('community.previewModel')
  if (preview.kind === 'image') return t('community.previewImage')
  return t('community.previewText')
}

function getPostTextSizeClass(post: PostItem) {
  const len = (post.content || '').trim().length
  if (len <= 40) return 'post-text-preview-large'
  if (len <= 120) return 'post-text-preview-medium'
  return 'post-text-preview-small'
}

function getPostModelName(post: PostItem) {
  const raw = (post.models || []).map((u) => normalizeMediaUrl(u)).find((u) => !!u) || ''
  if (!raw) return t('community.modelFileFallback')
  const sanitized = raw.split('?')[0]
  const name = sanitized.split('/').filter(Boolean).pop() || t('community.modelFileFallback')
  try {
    return decodeURIComponent(name)
  } catch {
    return name
  }
}

function getPostHiddenMediaCount(post: PostItem) {
  const total = (post.models?.length || 0) + (post.images?.length || 0) + (post.videos?.length || 0)
  const shown = getPostPreview(post).kind === 'text' ? 0 : 1
  return Math.max(0, total - shown)
}

function openPublishModal() {
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'community.loginRequiredPublish'
    loginPromptOpen.value = true
    return
  }
  publishOpen.value = true
}

function closePublishModal() {
  if (publishing.value) return
  publishOpen.value = false
  publishStatus.value = ''
}

function triggerPublishImageInput() {
  publishImageInput.value?.click()
}

function triggerPublishModelInput() {
  publishModelInput.value?.click()
}

function triggerPublishVideoInput() {
  publishVideoInput.value?.click()
}

function onImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  imageFiles.value = [...imageFiles.value, ...selected].slice(0, 9)
  input.value = ''
}

function onModelSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  modelFiles.value = [...modelFiles.value, ...selected].slice(0, 6)
  input.value = ''
}

function onVideoSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  videoFiles.value = [...videoFiles.value, ...selected].slice(0, 3)
  input.value = ''
}

function removeImage(idx: number) {
  imageFiles.value.splice(idx, 1)
}

function removeModel(idx: number) {
  modelFiles.value.splice(idx, 1)
}

function removeVideo(idx: number) {
  videoFiles.value.splice(idx, 1)
}

async function toggleLike(item: CommunityItem) {
  if (!item) return

  if (!auth.isAuthed) {
    loginPromptMessage.value = 'community.loginRequiredLike'
    loginPromptOpen.value = true
    return
  }

  try {
    const currentlyLiked = !!item.liked_by_me

    if (item.item_type === 'asset') {
      if (!currentlyLiked) {
        const res = await api.assets.like(item.id)
        item.stats.likes = res.likes
        item.liked_by_me = true
      } else {
        const res = await api.assets.unlike(item.id)
        item.stats.likes = res.likes
        item.liked_by_me = false
      }
    } else {
      if (!currentlyLiked) {
        const res = await api.community.likePost(item.id)
        item.stats.likes = res.likes
        item.liked_by_me = true
      } else {
        const res = await api.community.unlikePost(item.id)
        item.stats.likes = res.likes
        item.liked_by_me = false
      }
    }
  } catch (e: any) {
    const msg = e?.message || 'community.actionFailed'
    // 登录态失效交给全局 401 处理（自动跳转登录）
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    alert(typeof msg === 'string' && msg.startsWith('community.') ? t(msg) : msg)
  }
}

async function handlePreviewError(asset: AssetItem, e: Event) {
  // 仅尝试刷新一次，避免无限 error 循环
  if (!asset || asset._preview_refreshed_once) return
  asset._preview_refreshed_once = true
  try {
    const res = await api.assets.previewUrl(asset.id)
    if (res?.url) {
      asset.image_url = res.url
      const el = e?.target as HTMLImageElement | null
      if (el) {
        el.src = res.url
      }
    }
  } catch (err: any) {
    const msg = err?.message || ''
    // 登录态失效交给全局 401 处理（自动跳转登录），这里不再额外弹窗
    if (
      msg.includes('Invalid authentication credentials') ||
      msg.includes('401') ||
      msg.includes('未登录')
    ) {
      return
    }
    // 其他错误：静默处理，保留卡片背景色作为占位
  }
}

async function submitPost() {
  const content = postContent.value.trim()
  if (!content && !imageFiles.value.length && !modelFiles.value.length && !videoFiles.value.length) {
    alert(t('community.fillContentOrUpload'))
    return
  }

  publishing.value = true
  publishStatus.value = 'community.uploadingAssets'

  try {
    const imageUrls: string[] = []
    const modelUrls: string[] = []
    const videoUrls: string[] = []

    for (const f of imageFiles.value) {
      const res = await api.community.uploadPostImage(f)
      imageUrls.push(res.url)
    }

    for (const f of modelFiles.value) {
      const res = await api.community.uploadPostModel(f)
      modelUrls.push(res.url)
    }

    for (const f of videoFiles.value) {
      const res = await api.community.uploadPostVideo(f)
      videoUrls.push(res.url)
    }

    publishStatus.value = 'community.publishingPost'
    await api.community.createPost({
      content,
      images: imageUrls,
      models: modelUrls,
      videos: videoUrls,
    })

    publishStatus.value = ''
    postContent.value = ''
    imageFiles.value = []
    modelFiles.value = []
    videoFiles.value = []
    publishOpen.value = false
    await load()
  } catch (e: any) {
    publishStatus.value = e?.message || 'community.publishFailed'
  } finally {
    publishing.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.community.feed({ page: 1, page_size: 20, sort: sort.value })
    // 先把后端返回的条目 normalize 后再过滤掉需要临时隐藏的 id
    items.value = (res.items || [])
      .map((item: any) => normalizeCommunityItem(item))
      .filter((it: CommunityItem) => !BLOCKED_COMMUNITY_IDS.has((it as any).id))
  } catch (e: any) {
    error.value = e?.message || 'community.loadFailed'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/* 整体容器 */
.community-container {
  background-color: #161625;
  border-radius: 12px;
  padding: 24px;
  margin-top: 32px;
  transition: all 0.2s;
}

.community-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.community-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.community-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.community-btn-fixed {
  min-width: 116px;
  justify-content: center;
}

.community-publish-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #4f46e5, #6366f1); /* match bg-indigo-600 -> bg-indigo-500 */
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  height: 36px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.06);
}

.community-publish-btn:hover {
  background: #6366f1; /* indigo-500 on hover */
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.16);
}

.community-publish-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.community-sort-select {
  padding: 8px 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #f8fafc;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: all 0.2s;
  height: 36px;
  min-width: 132px;
}

.community-sort-select:hover {
  border-color: rgba(148, 163, 184, 0.3);
  background-color: #252538;
}

.community-sort-select:focus {
  border-color: #7B61FF;
  box-shadow: 0 0 0 3px rgba(123, 97, 255, 0.1);
}

.community-refresh-btn {
  padding: 8px 16px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  height: 36px;
  white-space: nowrap;
}

.community-refresh-btn:hover {
  background-color: #252538;
  border-color: rgba(148, 163, 184, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.community-loading,
.community-error {
  text-align: center;
  padding: 32px 0;
  color: #94a3b8;
}

.community-error {
  color: #f87171;
}

/* 网格布局 */
.community-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 24px;
}

@media (min-width: 640px) {
  .community-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .community-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 卡片组件 */
.asset-card {
  background-color: #1E1E2E;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  text-decoration: none;
  overflow: hidden;
}

.post-card {
  background-color: #1E1E2E;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.post-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.35);
}

.post-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.post-card-author {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
}

.post-card-time {
  color: #94a3b8;
  font-size: 12px;
}

.post-card-content {
  color: #e2e8f0;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.post-card-content-compact {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-media-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.post-preview-box {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.6);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.post-preview-body {
  min-height: 180px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: stretch;
}

.post-preview-box-text {
  min-height: 160px;
}

.post-preview-box-model .post-preview-body {
  background: linear-gradient(160deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.92));
}

.post-preview-box-image .post-preview-body {
  background: #0f172a;
}

.post-model-preview {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px;
  text-align: center;
}

.post-model-badge {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 30% 30%, #67e8f9, #2563eb);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.post-model-name {
  color: #e2e8f0;
  font-size: 13px;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.post-preview-meta {
  font-size: 12px;
  color: #93c5fd;
}

.post-hidden-meta {
  color: #94a3b8;
  font-size: 12px;
}

.post-media-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.post-text-preview {
  width: 100%;
  min-height: 180px;
  padding: 14px;
  margin: 0;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 7;
  -webkit-box-orient: vertical;
  overflow: hidden;
  background: linear-gradient(160deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.92));
}

.post-text-preview-large {
  font-size: clamp(20px, 2.2vw, 24px);
}

.post-text-preview-medium {
  font-size: clamp(16px, 1.8vw, 19px);
}

.post-text-preview-small {
  font-size: clamp(14px, 1.3vw, 16px);
}

.post-file-list,
.post-video-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.post-file-list.compact {
  flex-direction: row;
  gap: 6px;
}

.post-file-pill {
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  padding: 3px 8px;
  color: #cbd5e1;
  font-size: 12px;
}

.post-file-link {
  color: #e0f2fe;
  background: rgba(14, 165, 233, 0.2);
  border: 1px solid rgba(125, 211, 252, 0.4);
  border-radius: 999px;
  padding: 6px 12px;
  text-decoration: none;
  font-size: 13px;
}

.post-file-link:hover {
  text-decoration: underline;
}

.post-video {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.post-card-actions {
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.publish-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
  padding: 16px;
}

.publish-dialog {
  width: min(680px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 12px;
  background: #0f172a;
  border: 1px solid rgba(148, 163, 184, 0.25);
  padding: 16px;
}

.publish-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.publish-title {
  margin: 0;
  color: #f8fafc;
  font-size: 20px;
}

.publish-close {
  border: none;
  background: transparent;
  color: #cbd5e1;
  font-size: 24px;
  cursor: pointer;
}

.publish-textarea {
  width: 100%;
  min-height: 120px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: #111827;
  color: #f8fafc;
  padding: 12px;
  resize: vertical;
  margin-bottom: 16px;
}

.publish-upload-block {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 12px;
}

.publish-label {
  display: block;
  color: #cbd5e1;
  font-size: 13px;
  margin-bottom: 8px;
}

.publish-file-input-hidden {
  display: none;
}

.btn-image-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-image-select.community-btn-fixed {
  min-width: 132px;
}

.btn-image-select:hover {
  background-color: #252538;
  border-color: rgba(148, 163, 184, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.w-4 {
  width: 1rem;
}

.h-4 {
  height: 1rem;
}

.publish-file-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.publish-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  color: #cbd5e1;
  font-size: 13px;
}

.publish-file-item button {
  border: none;
  background: #334155;
  color: #f8fafc;
  border-radius: 6px;
  font-size: 12px;
  padding: 4px 8px;
  cursor: pointer;
}

.publish-status {
  color: #7dd3fc;
  font-size: 13px;
  margin: 8px 0;
}

.publish-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}

.asset-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
}

.asset-card-image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #0f172a;
}

.asset-card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.asset-card-tag {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 4px 8px;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  color: #ffffff;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
  border: 1px solid rgba(6, 182, 212, 0.3);
  z-index: 1;
}

.asset-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.asset-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.2s;
}

.asset-card:hover .asset-card-title {
  color: #a5b4fc;
}

.asset-card-author {
  font-size: 12px;
  color: #94a3b8;
  margin: 0 0 12px 0;
}

.asset-card-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.asset-stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #94a3b8;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  transition: all 0.2s;
}

.asset-stat-icon {
  width: 16px;
  height: 16px;
}

.asset-stat-like {
  cursor: pointer;
}

.asset-stat-like:hover {
  color: #f472b6;
}

.asset-stat-like-active {
  color: #f472b6;
}

@media (max-width: 640px) {
  .post-media-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
