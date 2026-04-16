<template>
  <div class="post-detail-container">
    <LoginPromptModal
      v-model:open="loginPromptOpen"
      :message="t(loginPromptMessage)"
      @goLogin="loginPromptOpen = false"
    />

    <ConfirmDialog
      v-model:open="deletePostDialogOpen"
      :title="t('postDetail.deletePostTitle')"
      :message="t('postDetail.deletePostMessage')"
      :confirm-text="t('postDetail.delete')"
      :cancel-text="t('postDetail.cancel')"
      @confirm="confirmDeletePost"
    />

    <ConfirmDialog
      v-model:open="deleteCommentDialogOpen"
      :title="t('postDetail.deleteCommentTitle')"
      :message="t('postDetail.deleteCommentMessage')"
      :confirm-text="t('postDetail.delete')"
      :cancel-text="t('postDetail.cancel')"
      @confirm="confirmDeleteComment"
    />

    <div v-if="loading" class="post-detail-loading">{{ t('postDetail.loading') }}</div>
    <div v-else-if="error" class="post-detail-error">{{ errorDisplay }}</div>

    <template v-else-if="post">
      <div class="post-detail-content">
        <section class="post-preview-section">
          <button class="post-back-btn" type="button" @click="router.push('/community')">
            ← {{ t('postDetail.backToCommunity') }}
          </button>

          <div class="post-preview-card">
            <h3 class="post-preview-title">{{ t('postDetail.mediaPreviewTitle') }}</h3>

            <div v-if="post.models.length" class="post-media-group">
              <h4 class="post-media-group-title">{{ t('postDetail.modelsTitle', { count: post.models.length }) }}</h4>
                <a
                v-for="(modelUrl, idx) in post.models"
                :key="`model-${idx}`"
                class="post-model-link"
                :href="resolveMediaUrl(modelUrl)"
                target="_blank"
                rel="noreferrer"
              >
                  {{ t('postDetail.open3dFileNumber', { index: idx + 1 }) }}
              </a>
            </div>

            <div v-if="post.images.length" class="post-media-group">
              <h4 class="post-media-group-title">{{ t('postDetail.imagesTitle', { count: post.images.length }) }}</h4>
              <div class="post-image-grid">
                <img
                  v-for="(img, idx) in post.images"
                  :key="`img-${idx}`"
                  class="post-image-item"
                  :src="resolveMediaUrl(img)"
                  :alt="t('postDetail.imageAlt')"
                />
              </div>
            </div>

            <div v-if="post.videos.length" class="post-media-group">
              <h4 class="post-media-group-title">{{ t('postDetail.videosTitle', { count: post.videos.length }) }}</h4>
              <div class="post-video-grid">
                <video
                  v-for="(videoUrl, idx) in post.videos"
                  :key="`video-${idx}`"
                  class="post-video-item"
                  :src="resolveMediaUrl(videoUrl)"
                  controls
                  preload="metadata"
                ></video>
              </div>
            </div>

            <p v-if="!post.models.length && !post.images.length && !post.videos.length" class="post-empty-media">
              {{ t('postDetail.noMediaOnlyText') }}
            </p>
          </div>
        </section>

        <section class="post-info-section">
          <div class="post-info-header">
            <h1 class="post-detail-title">{{ t('postDetail.title') }}</h1>
            <div class="post-header-actions">
              <div class="post-stat-badge post-stat-btn post-stat-comment" :title="t('postDetail.commentsCountTitle')">
                <svg class="post-stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span class="post-stat-value">{{ commentTotal }}</span>
              </div>
              <button
                class="post-stat-badge post-stat-btn post-stat-like"
                type="button"
                :class="{ 'post-stat-like-active': post.liked_by_me }"
                @click="togglePostLike"
                :title="t('postDetail.like')"
              >
                <svg class="post-stat-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                </svg>
                <span class="post-stat-value">{{ post.stats.likes }}</span>
              </button>
              <button
                v-if="canDeletePost"
                class="post-delete-btn"
                type="button"
                :disabled="deletingPost"
                @click="handleDeletePost"
              >
                {{ deletingPost ? t('postDetail.deleting') : t('postDetail.deletePost') }}
              </button>
            </div>
          </div>

          <div class="post-author-row">
            <!--
            <img
              :src="post.author_avatar || '/default-avatar.png'"
              class="post-author-avatar"
              :alt="post.author_name"
            />
            -->
            <span class="post-author-name">{{ t('community.authorPrefix') }}{{ post.author_name }}</span>
            <span class="post-author-time" v-if="post.created_at">{{ formatTime(post.created_at) }}</span>
          </div>

          <div class="post-content-box">
            <div class="post-content-label">{{ t('postDetail.contentLabel') }}</div>
            <p class="post-content-text">{{ post.content || t('postDetail.noContent') }}</p>
          </div>
        </section>
      </div>

      <section class="post-comment-section">
        <h2 class="post-comment-title">{{ t('postDetail.commentsTitle', { count: commentTotal }) }}</h2>

        <div v-if="auth.isAuthed" class="post-comment-input-wrap comment-input-area">
          <textarea
            v-model="commentContent"
            class="post-comment-textarea comment-textarea"
            :placeholder="t('postDetail.commentPlaceholder')"
            maxlength="1000"
          ></textarea>

          <div class="comment-input-actions">
            <div class="comment-input-left">
              <input
                ref="commentImageInput"
                type="file"
                accept="image/*"
                multiple
                class="comment-file-input-hidden"
                @change="onCommentImageSelect"
              />
              <input
                ref="commentVideoInput"
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                multiple
                class="comment-file-input-hidden"
                @change="onCommentVideoSelect"
              />
              <button class="btn-image-select" type="button" @click="triggerCommentImageInput">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ t('community.selectPhotos') }}
              </button>
              <button class="btn-image-select" type="button" @click="triggerCommentVideoInput">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
                </svg>
                {{ t('community.selectVideos') }}
              </button>
              <span class="post-comment-hint comment-image-hint">{{ t('postDetail.commentMediaHint') }}</span>
            </div>
            <div class="comment-input-right">
              <span class="comment-char-count" :class="{ 'comment-char-count-warning': commentContent.length >= 1000 }">
                ({{ commentContent.length }}/1000)
              </span>
                  <button
                    class="post-comment-submit btn-publish"
                    type="button"
                    :disabled="submittingComment || (!commentContent.trim() && !selectedCommentImages.length && !selectedCommentVideos.length)"
                    @click="submitComment"
                  >
                    {{ submittingComment ? t('postDetail.publishingComment') : t('postDetail.publishComment') }}
                  </button>
            </div>
          </div>

          <div v-if="selectedCommentImages.length" class="comment-image-preview">
            <div v-for="(img, idx) in selectedCommentImages" :key="`comment-img-${idx}`" class="comment-image-item">
              <img :src="img.preview" class="comment-image-preview-img" alt="selected image" />
              <button type="button" class="comment-image-remove" @click="removeCommentImage(idx)">×</button>
            </div>
          </div>

          <div v-if="selectedCommentVideos.length" class="comment-video-preview">
            <div v-for="(video, idx) in selectedCommentVideos" :key="`comment-video-${idx}`" class="comment-video-item">
              <video :src="video.preview" class="comment-video-preview-player" controls preload="metadata"></video>
              <div class="comment-video-name">{{ video.file.name }}</div>
              <button type="button" class="comment-image-remove" @click="removeCommentVideo(idx)">×</button>
            </div>
          </div>

        </div>
          <div v-else class="post-comment-login-hint">{{ t('postDetail.loginToCommentHint') }}</div>

        <div class="comment-sort-bar">
          <span class="comment-sort-label">{{ t('postDetail.filterAll') }}</span>
          <div class="comment-sort-actions">
            <button
              v-for="opt in sortOptions"
              :key="opt.value"
              class="comment-sort-btn"
              :class="{ 'comment-sort-btn-active': sortBy === opt.value }"
              type="button"
              @click="changeSort(opt.value)"
            >
              {{ t(opt.label) }}
            </button>
          </div>
        </div>

        <div v-if="commentsLoading" class="post-comment-loading">{{ t('postDetail.commentsLoading') }}</div>
        <div v-else-if="!comments.length" class="post-comment-empty">{{ t('postDetail.noComments') }}</div>
        <div v-else class="post-comment-list comment-list">
          <div v-for="comment in comments" :key="comment.id" class="post-comment-card comment-card">
            <div class="comment-card-content">
              <!--
              <img
                :src="comment.author_avatar || '/default-avatar.png'"
                class="comment-avatar"
                :alt="comment.author_name || t('postDetail.userAvatarAlt')"
              />
              -->
              <div class="comment-body">
                  <div class="post-comment-head comment-header">
                  <span class="post-comment-author comment-author">{{ comment.author_name || t('postDetail.anonymous') }}</span>
                  <button
                    v-if="canDeleteComment(comment)"
                    class="comment-delete-btn"
                    type="button"
                    @click="deleteComment(comment.id)"
                  >
                    {{ t('postDetail.delete') }}
                  </button>
                </div>

                <p class="post-comment-content comment-text">{{ comment.content }}</p>

                <div v-if="comment.images?.length" class="comment-images">
                  <img
                    v-for="(img, idx) in comment.images"
                    :key="`comment-${comment.id}-img-${idx}`"
                    :src="resolveMediaUrl(img)"
                    class="comment-image"
                    alt="comment image"
                  />
                </div>

                <div v-if="comment.videos?.length" class="comment-videos">
                  <video
                    v-for="(video, idx) in comment.videos"
                    :key="`comment-${comment.id}-video-${idx}`"
                    :src="resolveMediaUrl(video)"
                    class="comment-video"
                    controls
                    preload="metadata"
                  ></video>
                </div>

                <div class="comment-meta-actions">
                  <span class="post-comment-time comment-time">{{ formatTime(comment.created_at) }}</span>
                  <div class="post-comment-tools comment-actions">
                    <button
                      class="post-comment-tool-btn comment-action-btn"
                      type="button"
                      :class="{ 'post-comment-like-active': !!comment.liked_by_me }"
                      @click="toggleCommentLike(comment)"
                    >
                      👍 {{ comment.like_count || 0 }}
                    </button>
                    <button class="post-comment-tool-btn comment-action-btn" type="button" @click="toggleReplyEditor(comment.id)">
                      {{ t('postDetail.reply') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

                  <div v-if="replyEditorOpen[comment.id]" class="post-reply-editor">
                <textarea
                v-model="replyDraft[comment.id]"
                class="post-comment-textarea reply comment-textarea comment-textarea-sm"
                :placeholder="t('postDetail.replyPlaceholder')"
                maxlength="1000"
              ></textarea>

              <div class="comment-reply-input-actions">
                <div class="comment-input-left">
                  <input
                    :ref="(el) => setReplyImageInputRef(comment.id, el)"
                    type="file"
                    accept="image/*"
                    multiple
                    class="comment-file-input-hidden"
                    @change="(e) => onReplyImageSelect(comment.id, e)"
                  />
                  <input
                    :ref="(el) => setReplyVideoInputRef(comment.id, el)"
                    type="file"
                    accept="video/mp4,video/webm,video/quicktime"
                    multiple
                    class="comment-file-input-hidden"
                    @change="(e) => onReplyVideoSelect(comment.id, e)"
                  />
                    <button class="btn-image-select btn-image-select-sm" type="button" @click="triggerReplyImageInput(comment.id)">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {{ t('community.selectPhotos') }}
                  </button>
                  <button class="btn-image-select btn-image-select-sm" type="button" @click="triggerReplyVideoInput(comment.id)">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
                    </svg>
                    {{ t('community.selectVideos') }}
                  </button>
                </div>
                <div class="comment-input-right">
                  <span class="comment-char-count comment-char-count-sm" :class="{ 'comment-char-count-warning': (replyDraft[comment.id] || '').length >= 1000 }">
                    ({{ (replyDraft[comment.id] || '').length }}/1000)
                  </span>
                  <button class="btn-cancel-sm" type="button" @click="cancelReplyEditor(comment.id)">{{ t('postDetail.cancel') }}</button>
                  <button
                    class="post-comment-submit btn-publish btn-publish-sm"
                    type="button"
                    :disabled="!!replySubmitting[comment.id] || (!getReplyText(comment.id) && !getReplyImages(comment.id).length && !getReplyVideos(comment.id).length)"
                    @click="submitReply(comment.id)"
                  >
                    {{ replySubmitting[comment.id] ? t('postDetail.replying') : t('postDetail.publishReply') }}
                  </button>
                </div>
              </div>

              <div v-if="replyImages[comment.id]?.length" class="comment-image-preview">
                <div v-for="(img, idx) in replyImages[comment.id]" :key="`reply-${comment.id}-img-${idx}`" class="comment-image-item comment-image-item-sm">
                  <img :src="img.preview" class="comment-image-preview-img comment-image-preview-img-sm" alt="reply selected image" />
                  <button type="button" class="comment-image-remove comment-image-remove-sm" @click="removeReplyImage(comment.id, idx)">×</button>
                </div>
              </div>

              <div v-if="replyVideos[comment.id]?.length" class="comment-video-preview">
                <div v-for="(video, idx) in replyVideos[comment.id]" :key="`reply-${comment.id}-video-${idx}`" class="comment-video-item comment-video-item-sm">
                  <video :src="video.preview" class="comment-video-preview-player comment-video-preview-player-sm" controls preload="metadata"></video>
                  <div class="comment-video-name">{{ video.file.name }}</div>
                  <button type="button" class="comment-image-remove comment-image-remove-sm" @click="removeReplyVideo(comment.id, idx)">×</button>
                </div>
              </div>
            </div>

            <div v-if="comment.replies?.length" class="post-reply-list">
              <div v-for="reply in comment.replies" :key="reply.id" class="post-reply-item reply-wrapper">
                <div class="comment-card-content">
                  <!--
                  <img
                    :src="reply.author_avatar || '/default-avatar.png'"
                    class="comment-avatar"
                        :alt="reply.author_name || t('postDetail.userAvatarAlt')"
                  />
                  -->
                  <div class="comment-body">
                    <div class="post-comment-head comment-header">
                      <div class="comment-author-line">
                        <span class="post-comment-author comment-author">{{ reply.author_name || t('postDetail.anonymous') }}</span>
                        <span v-if="reply.reply_to_name" class="comment-reply-to">{{ t('postDetail.replyTo') }} @{{ reply.reply_to_name }}</span>
                      </div>
                      <button
                        v-if="canDeleteComment(reply)"
                        class="comment-delete-btn"
                        type="button"
                        @click="deleteComment(reply.id)"
                      >
                        {{ t('postDetail.delete') }}
                      </button>
                    </div>

                    <p class="post-comment-content comment-text">{{ reply.content }}</p>

                    <div v-if="reply.images?.length" class="comment-images">
                      <img
                        v-for="(img, idx) in reply.images"
                        :key="`reply-${reply.id}-img-${idx}`"
                        :src="resolveMediaUrl(img)"
                        class="comment-image"
                        alt="reply image"
                      />
                    </div>

                    <div v-if="reply.videos?.length" class="comment-videos">
                      <video
                        v-for="(video, idx) in reply.videos"
                        :key="`reply-${reply.id}-video-${idx}`"
                        :src="resolveMediaUrl(video)"
                        class="comment-video"
                        controls
                        preload="metadata"
                      ></video>
                    </div>

                    <div class="comment-meta-actions">
                      <span class="post-comment-time comment-time">{{ formatTime(reply.created_at) }}</span>
                      <div class="post-comment-tools comment-actions">
                        <button
                          class="post-comment-tool-btn comment-action-btn"
                          type="button"
                          :class="{ 'post-comment-like-active': !!reply.liked_by_me }"
                          @click="toggleCommentLike(reply)"
                        >
                          👍 {{ reply.like_count || 0 }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="post-detail-error">{{ t('postDetail.postNotFound') }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import LoginPromptModal from '../components/LoginPromptModal.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { api, resolveMediaUrl } from '../lib/api'
import { useAuthStore } from '../stores/auth'

type PostDetail = {
  id: string
  author_id?: string | null
  author_name: string
  author_avatar?: string | null
  content: string
  images: string[]
  models: string[]
  videos: string[]
  created_at?: string | null
  updated_at?: string | null
  liked_by_me?: boolean
  stats: { likes: number }
}

type PostComment = {
  id: string
  post_id: string
  author_id?: string | null
  author_name: string
  author_avatar?: string | null
  reply_to_name?: string | null
  parent_id?: string | null
  content: string
  images?: string[]
  videos?: string[]
  like_count: number
  reply_count: number
  created_at: string
  liked_by_me?: boolean
  replies?: PostComment[]
}

type SelectedFile = { file: File; preview: string }

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
auth.hydrate()

const loading = ref(false)
const error = ref('')
const post = ref<PostDetail | null>(null)
const deletingPost = ref(false)

const commentsLoading = ref(false)
const comments = ref<PostComment[]>([])
const commentTotal = ref(0)
const sortBy = ref<'new' | 'liked' | 'replied'>('new')
const sortOptions: Array<{ value: 'new' | 'liked' | 'replied'; label: string }> = [
  { value: 'new', label: 'postDetail.sortNew' },
  { value: 'liked', label: 'postDetail.sortLiked' },
  { value: 'replied', label: 'postDetail.sortReplied' },
]
const commentContent = ref('')
const selectedCommentImages = ref<SelectedFile[]>([])
const selectedCommentVideos = ref<SelectedFile[]>([])
const submittingComment = ref(false)

const replyEditorOpen = reactive<Record<string, boolean>>({})
const replyDraft = ref<Record<string, string>>({})
const replyImages = ref<Record<string, SelectedFile[]>>({})
const replyVideos = ref<Record<string, SelectedFile[]>>({})
const replySubmitting = ref<Record<string, boolean>>({})
const commentImageInput = ref<HTMLInputElement | null>(null)
const commentVideoInput = ref<HTMLInputElement | null>(null)
const replyImageInputs = ref<Record<string, HTMLInputElement | null>>({})
const replyVideoInputs = ref<Record<string, HTMLInputElement | null>>({})

const { t } = useI18n()

const loginPromptOpen = ref(false)
const loginPromptMessage = ref('postDetail.loginRequired')
const deletePostDialogOpen = ref(false)
const deleteCommentDialogOpen = ref(false)
const pendingDeleteCommentId = ref('')

const postId = computed(() => String(route.params.id || ''))
const canDeletePost = computed(() => {
  if (!post.value || !auth.user?.id || !post.value.author_id) return false
  return String(auth.user.id) === String(post.value.author_id)
})

function formatTime(raw?: string | null) {
  if (!raw) return t('postDetail.justNow')
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return t('postDetail.justNow')
  return d.toLocaleString()
}

const errorDisplay = computed(() => {
  const v = error.value
  if (typeof v === 'string' && v.startsWith('postDetail.')) return t(v)
  return v
})

function showAlert(msg: any) {
  let text = ''
  if (!msg) text = ''
  else if (typeof msg === 'string') text = msg
  else if (typeof msg === 'object' && msg.message) text = msg.message
  else text = String(msg)

  if (text && text.startsWith('postDetail.')) {
    alert(t(text))
  } else {
    alert(text)
  }
}

async function withTimeout<T>(promise: Promise<T>, ms: number, timeoutMsg: string): Promise<T> {
  let timer: any
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(timeoutMsg)), ms)
  })
  try {
    return await Promise.race([promise, timeout])
  } finally {
    clearTimeout(timer)
  }
}

function canDeleteComment(comment: PostComment) {
  if (!auth.user?.id || !comment.author_id) return false
  return String(auth.user.id) === String(comment.author_id)
}

function flattenReplyComments(items: PostComment[] = []): PostComment[] {
  const result: PostComment[] = []
  for (const item of items) {
    result.push(item)
    if (item.replies?.length) {
      result.push(...flattenReplyComments(item.replies))
    }
  }
  return result
}

async function loadDetail() {
  if (!postId.value) {
    error.value = 'postDetail.invalidPostId'
    return
  }
  loading.value = true
  error.value = ''
  try {
    post.value = await withTimeout(
      api.community.getPostDetail(postId.value),
      15000,
      'postDetail.loadTimeout'
    )
  } catch (e: any) {
    post.value = null
    error.value = e?.message || 'postDetail.loadDetailFailed'
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  if (!postId.value) return
  commentsLoading.value = true
  try {
    const res = await withTimeout(
      api.community.getPostComments(postId.value, { page: 1, page_size: 100, sort: sortBy.value }),
      15000,
      'postDetail.loadCommentsTimeout'
    )
    comments.value = res.items || []
    commentTotal.value = res.total || 0
  } catch {
    comments.value = []
    commentTotal.value = 0
  } finally {
    commentsLoading.value = false
  }
}

function onCommentImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  const mapped = files.map((file) => ({ file, preview: URL.createObjectURL(file) }))
  selectedCommentImages.value = [...selectedCommentImages.value, ...mapped].slice(0, 10)
  input.value = ''
}

function onCommentVideoSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  const mapped = files.map((file) => ({ file, preview: URL.createObjectURL(file) }))
  selectedCommentVideos.value = [...selectedCommentVideos.value, ...mapped].slice(0, 3)
  input.value = ''
}

function removeCommentImage(index: number) {
  const item = selectedCommentImages.value[index]
  if (item?.preview) URL.revokeObjectURL(item.preview)
  selectedCommentImages.value.splice(index, 1)
}

function removeCommentVideo(index: number) {
  const item = selectedCommentVideos.value[index]
  if (item?.preview) URL.revokeObjectURL(item.preview)
  selectedCommentVideos.value.splice(index, 1)
}

function getReplyText(parentId: string) {
  return (replyDraft.value[parentId] || '').trim()
}

function getReplyImages(parentId: string) {
  return replyImages.value[parentId] || []
}

function getReplyVideos(parentId: string) {
  return replyVideos.value[parentId] || []
}

function toggleReplyEditor(parentId: string) {
  replyEditorOpen[parentId] = !replyEditorOpen[parentId]
  if (replyEditorOpen[parentId] && !replyDraft.value[parentId]) {
    replyDraft.value[parentId] = ''
  }
}

function cancelReplyEditor(parentId: string) {
  resetReplyDraft(parentId)
}

function changeSort(sort: 'new' | 'liked' | 'replied') {
  if (sortBy.value === sort) return
  sortBy.value = sort
  loadComments()
}

function triggerCommentImageInput() {
  commentImageInput.value?.click()
}

function triggerCommentVideoInput() {
  commentVideoInput.value?.click()
}

function setReplyImageInputRef(parentId: string, el: unknown) {
  replyImageInputs.value[parentId] = (el as HTMLInputElement | null) || null
}

function setReplyVideoInputRef(parentId: string, el: unknown) {
  replyVideoInputs.value[parentId] = (el as HTMLInputElement | null) || null
}

function triggerReplyImageInput(parentId: string) {
  replyImageInputs.value[parentId]?.click()
}

function triggerReplyVideoInput(parentId: string) {
  replyVideoInputs.value[parentId]?.click()
}

function onReplyImageSelect(parentId: string, e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  const mapped = files.map((file) => ({ file, preview: URL.createObjectURL(file) }))
  const curr = replyImages.value[parentId] || []
  replyImages.value[parentId] = [...curr, ...mapped].slice(0, 10)
  input.value = ''
}

function onReplyVideoSelect(parentId: string, e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  const mapped = files.map((file) => ({ file, preview: URL.createObjectURL(file) }))
  const curr = replyVideos.value[parentId] || []
  replyVideos.value[parentId] = [...curr, ...mapped].slice(0, 3)
  input.value = ''
}

function removeReplyImage(parentId: string, index: number) {
  const arr = replyImages.value[parentId] || []
  const item = arr[index]
  if (item?.preview) URL.revokeObjectURL(item.preview)
  arr.splice(index, 1)
  replyImages.value[parentId] = [...arr]
}

function removeReplyVideo(parentId: string, index: number) {
  const arr = replyVideos.value[parentId] || []
  const item = arr[index]
  if (item?.preview) URL.revokeObjectURL(item.preview)
  arr.splice(index, 1)
  replyVideos.value[parentId] = [...arr]
}

async function uploadCommentMedia(images: SelectedFile[], videos: SelectedFile[]) {
  const imageUrls: string[] = []
  const videoUrls: string[] = []

  for (const img of images) {
    const uploaded = await api.community.uploadPostCommentImage(img.file)
    imageUrls.push(uploaded.url)
  }
  for (const video of videos) {
    const uploaded = await api.community.uploadPostCommentVideo(video.file)
    videoUrls.push(uploaded.url)
  }

  return { imageUrls, videoUrls }
}

function resetMainCommentDraft() {
  for (const item of selectedCommentImages.value) {
    if (item.preview) URL.revokeObjectURL(item.preview)
  }
  for (const item of selectedCommentVideos.value) {
    if (item.preview) URL.revokeObjectURL(item.preview)
  }
  commentContent.value = ''
  selectedCommentImages.value = []
  selectedCommentVideos.value = []
}

function resetReplyDraft(parentId: string) {
  for (const item of replyImages.value[parentId] || []) {
    if (item.preview) URL.revokeObjectURL(item.preview)
  }
  for (const item of replyVideos.value[parentId] || []) {
    if (item.preview) URL.revokeObjectURL(item.preview)
  }
  replyDraft.value[parentId] = ''
  replyImages.value[parentId] = []
  replyVideos.value[parentId] = []
  replyEditorOpen[parentId] = false
}

async function togglePostLike() {
  if (!post.value) return
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'postDetail.loginToLike'
    loginPromptOpen.value = true
    return
  }

  try {
    if (post.value.liked_by_me) {
      const res = await api.community.unlikePost(post.value.id)
      post.value.liked_by_me = false
      post.value.stats.likes = res.likes
    } else {
      const res = await api.community.likePost(post.value.id)
      post.value.liked_by_me = true
      post.value.stats.likes = res.likes
    }
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.actionFailed')
  }
}

async function handleDeletePost() {
  if (!post.value || !canDeletePost.value || deletingPost.value) return
  deletePostDialogOpen.value = true
}

async function confirmDeletePost() {
  if (!post.value || !canDeletePost.value || deletingPost.value) return
  deletingPost.value = true
  try {
    await api.community.deletePost(post.value.id)
    router.push('/community')
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.deleteFailed')
  } finally {
    deletingPost.value = false
  }
}

async function submitComment() {
  const content = commentContent.value.trim()
  if (!content && !selectedCommentImages.value.length && !selectedCommentVideos.value.length) return

  if (!auth.isAuthed) {
    loginPromptMessage.value = 'postDetail.loginToComment'
    loginPromptOpen.value = true
    return
  }

  submittingComment.value = true
  try {
    const { imageUrls, videoUrls } = await uploadCommentMedia(selectedCommentImages.value, selectedCommentVideos.value)
    await api.community.createPostComment(postId.value, {
      content,
      images: imageUrls,
      videos: videoUrls,
    })
    resetMainCommentDraft()
    await loadComments()
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.commentPublishFailed')
  } finally {
    submittingComment.value = false
  }
}

async function submitReply(parentId: string) {
  const content = getReplyText(parentId)
  const images = getReplyImages(parentId)
  const videos = getReplyVideos(parentId)
  if (!content && !images.length && !videos.length) return

  if (!auth.isAuthed) {
    loginPromptMessage.value = 'postDetail.loginToReply'
    loginPromptOpen.value = true
    return
  }

  replySubmitting.value[parentId] = true
  try {
    const { imageUrls, videoUrls } = await uploadCommentMedia(images, videos)
    await api.community.createPostComment(postId.value, {
      content,
      parent_id: parentId,
      images: imageUrls,
      videos: videoUrls,
    })
    resetReplyDraft(parentId)
    await loadComments()
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.replyFailed')
  } finally {
    replySubmitting.value[parentId] = false
  }
}

async function deleteComment(commentId: string) {
  pendingDeleteCommentId.value = commentId
  deleteCommentDialogOpen.value = true
}

async function confirmDeleteComment() {
  if (!pendingDeleteCommentId.value) return
  try {
    await api.community.deletePostComment(postId.value, pendingDeleteCommentId.value)
    pendingDeleteCommentId.value = ''
    await loadComments()
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.deleteCommentFailed')
  }
}

async function toggleCommentLike(comment: PostComment) {
  if (!auth.isAuthed) {
    loginPromptMessage.value = 'postDetail.loginToLikeComment'
    loginPromptOpen.value = true
    return
  }

  try {
    if (comment.liked_by_me) {
      await api.community.unlikePostComment(postId.value, comment.id)
      comment.liked_by_me = false
      comment.like_count = Math.max(0, (comment.like_count || 0) - 1)
    } else {
      await api.community.likePostComment(postId.value, comment.id)
      comment.liked_by_me = true
      comment.like_count = (comment.like_count || 0) + 1
    }
  } catch (e: any) {
    showAlert(e?.message || 'postDetail.actionFailed')
  }
}

onMounted(async () => {
  await loadDetail()
  if (post.value) {
    await loadComments()
  }
})
</script>

<style scoped>
.post-detail-container {
  background-color: #161625;
  border-radius: 12px;
  padding: 24px;
  margin-top: 24px;
}

.post-detail-loading,
.post-detail-error {
  text-align: center;
  color: #cbd5e1;
  padding: 24px;
}

.post-detail-error {
  color: #f87171;
}

.post-detail-content {
  display: grid;
  gap: 18px;
  grid-template-columns: 1.2fr 1fr;
}

.post-preview-section,
.post-info-section,
.post-comment-section {
  background: #1b2436;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  padding: 18px;
}

.post-back-btn {
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: #0f172a;
  color: #cbd5e1;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  margin-bottom: 14px;
}

.post-preview-title {
  color: #f8fafc;
  margin: 0 0 12px;
}

.post-media-group {
  margin-bottom: 14px;
}

.post-media-group-title {
  margin: 0 0 8px;
  color: #e2e8f0;
  font-size: 14px;
}

.post-model-link {
  display: inline-flex;
  color: #7dd3fc;
  font-size: 13px;
  text-decoration: none;
  margin-right: 10px;
  margin-bottom: 6px;
}

.post-image-grid,
.post-video-grid,
.post-comment-media-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.post-image-item,
.post-video-item,
.post-comment-media-image,
.post-comment-media-video {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.post-empty-media {
  color: #94a3b8;
  font-size: 13px;
}

.post-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.post-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.post-stat-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.7);
  color: #cbd5e1;
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 13px;
}

.post-stat-btn {
  transition: all 0.2s;
}

.post-stat-btn:hover {
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(30, 41, 59, 0.9);
}

.post-stat-icon {
  width: 16px;
  height: 16px;
  color: currentColor;
}

.post-stat-value {
  font-size: 13px;
  font-weight: 600;
  color: currentColor;
}

.post-detail-title {
  margin: 0;
  color: #f8fafc;
  font-size: 26px;
}

.post-delete-btn {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(15, 23, 42, 0.8);
  color: #cbd5e1;
  border-radius: 999px;
  padding: 7px 12px;
  cursor: pointer;
}

.post-delete-btn {
  border-radius: 8px;
}

.post-stat-like:hover,
.post-stat-like-active {
  color: #fbcfe8;
  border-color: rgba(244, 114, 182, 0.5);
  background: rgba(157, 23, 77, 0.45);
}

.post-author-row {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.post-author-avatar {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  object-fit: cover;
}

.post-author-name,
.post-author-time {
  color: #cbd5e1;
  font-size: 13px;
}

.post-content-box {
  margin-top: 14px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  padding: 12px;
}

.post-content-label {
  font-size: 12px;
  color: #93c5fd;
  margin-bottom: 8px;
}

.post-content-text {
  margin: 0;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}

.post-comment-section {
  margin-top: 16px;
}

.post-comment-title {
  color: #f8fafc;
  margin: 0 0 12px;
}

.post-comment-input-wrap {
  margin-bottom: 12px;
}

.comment-input-area {
  margin-bottom: 18px;
}

.post-comment-textarea {
  width: 100%;
  min-height: 90px;
  background: #111827;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 8px;
  color: #f8fafc;
  padding: 10px;
  resize: vertical;
}

.post-comment-textarea.reply {
  min-height: 70px;
}

.post-comment-upload-tools {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.post-comment-hint {
  color: #94a3b8;
  font-size: 12px;
}

.comment-textarea {
  min-height: 100px;
  border-radius: 10px;
}

.comment-input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.comment-input-left,
.comment-input-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.comment-file-input-hidden {
  display: none;
}

.btn-image-select {
  display: flex;
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

.btn-image-select:hover {
  background-color: #252538;
  border-color: rgba(148, 163, 184, 0.3);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.btn-image-select-sm {
  padding: 6px 10px;
  font-size: 12px;
}

.w-4 {
  width: 1rem;
}

.h-4 {
  height: 1rem;
}

.w-3 {
  width: 0.75rem;
}

.h-3 {
  height: 0.75rem;
}

.comment-char-count {
  font-size: 12px;
  color: #94a3b8;
}

.comment-char-count-warning {
  color: #f87171;
}

.comment-char-count-sm {
  font-size: 11px;
}

.btn-publish {
  background: #7B61FF;
}

.btn-publish:hover:not(:disabled) {
  background: #6B51E6;
}

.btn-publish-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-cancel-sm {
  padding: 6px 12px;
  background-color: #1E1E2E;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel-sm:hover {
  background-color: #252538;
  color: #ffffff;
}

.comment-image-hint {
  font-size: 11px;
  color: #64748b;
}

.comment-image-preview,
.comment-video-preview {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.comment-image-item,
.comment-video-item {
  position: relative;
  transition: transform 0.2s;
}

.comment-image-item:hover,
.comment-video-item:hover {
  transform: translateY(-2px);
}

.comment-video-item {
  width: 160px;
}

.comment-video-item-sm {
  width: 140px;
}

.comment-image-preview-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.comment-image-preview-img-sm {
  width: 64px;
  height: 64px;
}

.comment-video-preview-player {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background-color: #0f172a;
}

.comment-video-preview-player-sm {
  height: 80px;
}

.comment-video-name {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comment-image-remove {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #ef4444;
  color: #ffffff;
  font-size: 12px;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.comment-image-item:hover .comment-image-remove,
.comment-video-item:hover .comment-image-remove {
  opacity: 1;
}

.comment-image-remove-sm {
  width: 16px;
  height: 16px;
  font-size: 10px;
}

.post-selected-media-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.post-selected-media-item {
  position: relative;
}

.post-selected-image,
.post-selected-video {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.post-remove-selected {
  position: absolute;
  top: 4px;
  right: 4px;
  border: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.85);
  color: #fff;
  cursor: pointer;
}

.post-comment-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.post-comment-submit {
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  padding: 8px 14px;
  cursor: pointer;
}

.post-comment-login-hint,
.post-comment-empty,
.post-comment-loading {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 10px;
}

.comment-sort-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.comment-sort-label {
  color: #94a3b8;
  font-size: 13px;
}

.comment-sort-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-sort-btn {
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  padding: 6px 12px;
  cursor: pointer;
}

.comment-sort-btn-active {
  background: #7B61FF;
  color: #fff;
}

.post-comment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-list {
  gap: 14px;
}

.post-comment-card,
.post-reply-item,
.post-reply-editor {
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.5);
  padding: 10px;
}

.comment-card {
  background-color: #1E1E2E;
  border-radius: 10px;
  padding: 14px;
  transition: all 0.2s;
}

.comment-card-content {
  display: flex;
  gap: 12px;
}

.comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(148, 163, 184, 0.2);
  flex-shrink: 0;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
}

.post-comment-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.post-comment-author {
  color: #f8fafc;
  font-size: 13px;
  font-weight: 600;
}

.post-comment-time {
  color: #94a3b8;
  font-size: 12px;
}

.post-comment-content {
  margin: 0;
  color: #cbd5e1;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-meta-actions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.comment-delete-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
}

.comment-card:hover .comment-delete-btn {
  opacity: 1;
}

.comment-delete-btn:hover {
  color: #f87171;
}

.comment-author-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-reply-to {
  font-size: 12px;
  color: #a5b4fc;
}

.comment-images,
.comment-videos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.comment-image,
.comment-video {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #0f172a;
}

.post-comment-tools {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.comment-actions {
  gap: 12px;
}

.post-comment-tool-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}

.comment-action-btn {
  transition: color 0.2s;
}

.comment-action-btn:hover {
  color: #cbd5e1;
}

.post-comment-tool-btn.danger {
  color: #fca5a5;
}

.post-comment-like-active {
  color: #f472b6;
}

.post-reply-editor {
  margin-top: 10px;
}

.comment-reply-input-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.post-reply-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 12px;
  border-left: 2px solid rgba(148, 163, 184, 0.15);
}

@media (max-width: 900px) {
  .post-detail-content {
    grid-template-columns: 1fr;
  }

  .post-image-grid,
  .post-video-grid,
  .post-comment-media-grid {
    grid-template-columns: 1fr;
  }

  .post-selected-media-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
